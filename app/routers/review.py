from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from app.models import *
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import jwt, JWTError
from sqlalchemy import insert, select, update, join
from sqlalchemy.orm import Session, join
from .auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update
from app.backend.db_depends import get_db
from app.schemas import CreateProduct, CreateReview
from slugify import slugify

router = APIRouter(prefix='/reviews', tags=['reviews'])


@router.get('/all_reviews')
async def all_reviews(db: Annotated[AsyncSession, Depends(get_db)]):
    reviews = await db.scalars(select(Review).where(Review.is_active == True))
    if reviews is None:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no reviews'
        )
    return reviews.all()


@router.get('/products_reviews')
async def products_reviews(db: Annotated[AsyncSession, Depends(get_db)], product_slug: str):
    product = await db.scalar(select(Product.id).filter(Product.slug == product_slug))
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no such product',
        )
    query = select(Review.comment, Rating.grade).join(Rating).where(Review.product_id == product, Review.is_active == True)
    reviews = await db.execute(query)
    response = {f'Отзыв {n}': f'{k[0]}. Оценка: {k[1]}' for n, k in enumerate(reviews, start=1)}

    if not len(response):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no reviews'
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
    current_rating_id = current_rating.inserted_primary_key[0]
    await db.execute(insert(Review).values(user_id=get_user.get('id'),
                                           product_id=product.id,
                                           rating_id=current_rating_id,
                                           comment=create_review.comment,
                                           ))

    all_reviews_current_product = await db.scalars(select(Review).where(Review.product_id == product.id))
    all_id_ratings_current_product = [rev_cur_prod.rating_id for rev_cur_prod in all_reviews_current_product.all()]
    all_ratings_current_product = await db.scalars(
        select(Rating).filter(Rating.id.in_(all_id_ratings_current_product), Rating.is_active == True))
    all_grade = [r.grade for r in all_ratings_current_product.all()]
    avg_rating = round(sum(all_grade)/len(all_grade), 1)
    await db.execute(update(Product).where(Product.id == product.id).values(
        rating=avg_rating,
    ))

    await db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful',
    }
