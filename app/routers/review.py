from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.backend.db_depends import get_db
from app.models import Product, Rating, Review
from app.schemas import CreateReview

from .auth import get_current_user

router = APIRouter(prefix='/reviews', tags=['reviews'])


@router.get('/all_reviews')
async def all_reviews(db: Annotated[AsyncSession, Depends(get_db)]):
    reviews = await db.scalars(select(Review).where(Review.is_active == True))
    if reviews is None:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no reviews',
        )
    return reviews.all()


@router.get('/products_reviews')
async def products_reviews(db: Annotated[AsyncSession, Depends(get_db)], product_slug: str):
    product = await db.scalar(select(Product.id).where(Product.slug == product_slug, Product.is_active == True))
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no such product',
        )
    query = select(Review.comment, Rating.grade).join(Rating).where(Review.product_id == product,
                                                                    Review.is_active == True)
    reviews = await db.execute(query)
    response = {k: v for k, v in reviews}  # ответ клиенту (key - отзыв, value - оценка)

    if not len(response):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no reviews',
        )
    return response


@router.post('/add_review')
async def add_review(db: Annotated[AsyncSession, Depends(get_db)], get_user: Annotated[dict, Depends(get_current_user)],
                     product_slug: str, create_review: CreateReview):
    product = await db.scalar(select(Product).filter(Product.slug == product_slug, Product.is_active == True))
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no such product',
        )

    current_rating = await db.execute(insert(Rating).values(
        grade=create_review.grade,
        user_id=get_user.get('id'),
        product_id=product.id,
    ))

    await db.execute(insert(Review).values(user_id=get_user.get('id'),
                                           product_id=product.id,
                                           rating_id=current_rating.inserted_primary_key[0],
                                           comment=create_review.comment,
                                           ))

    # пересчитываем средний рейтинг товара
    all_ratings_review_product = await db.scalars(select(Rating).where(Rating.product_id == product.id,
                                                                       Rating.is_active == True))
    all_grade = [r.grade for r in all_ratings_review_product.all()]
    avg_rating = round(sum(all_grade) / len(all_grade), 1)
    await db.execute(update(Product).where(Product.id == product.id).values(rating=avg_rating))
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful',
    }


@router.delete('/delete_reviews')
async def delete_reviews(db: Annotated[AsyncSession, Depends(get_db)],
                         get_user: Annotated[dict, Depends(get_current_user)],
                         review_id: int):
    if not get_user.get('is_admin'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have admin permission",
        )

    review_for_deletion = await db.scalar(select(Review).where(Review.id == review_id, Review.is_active == True))
    if review_for_deletion is None:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no review',
        )

    await db.execute(update(Review).where(Review.id == review_id).values(is_active=False))
    await db.execute(update(Rating).where(Rating.id == review_for_deletion.rating_id).values(is_active=False))

    # пересчитываем средний рейтинг товара без учёта удалённого отзыва
    all_ratings_review_product = await db.scalars(select(Rating).where(Rating.product_id == review_for_deletion.product_id,
                                                                       Rating.is_active == True))
    all_grade = [r.grade for r in all_ratings_review_product.all()]
    avg_rating = round(sum(all_grade) / len(all_grade), 1)
    await db.execute(update(Product).where(Product.id == review_for_deletion.product_id).values(rating=avg_rating))
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Review delete is successful',
    }
