from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from app.models import *
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from sqlalchemy import insert, select, update
from app.backend.db_depends import get_db
from app.schemas import CreateProduct
from slugify import slugify

router = APIRouter(prefix='/products', tags=['products'])


@router.get('/')
async def all_products(db: Annotated[Session, Depends(get_db)]):
    all_active_products = db.scalars(select(Product).where(Product.is_active == True)).all()
    return all_active_products


@router.post('/create')
async def create_product(db: Annotated[Session, Depends(get_db)], create_product: CreateProduct):
    db.execute(insert(Product).values(name=create_product.name,
                                      slug=slugify(create_product.name),
                                      description=create_product.description,
                                      price=create_product.price,
                                      image_url=create_product.image_url,
                                      stock=create_product.stock,
                                      category_id=create_product.category,
                                      rating=0.0,
                                      ))
    db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful',
    }


@router.get('/{category_slug}')
async def product_by_category(db: Annotated[Session, Depends(get_db)], category_slug: str):
    category = db.scalar(select(Category).where(Category.slug == category_slug))
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found',
        )

    subcategories = db.scalars(select(Category).where(Category.parent_id == category.id))
    requried_category_id = [s.id for s in subcategories.all()]
    requried_category_id.append(category.id)

    req_products = db.scalars(select(Product).filter(Product.category_id.in_(requried_category_id), Product.stock > 0,
                                                     Product.is_active == True)).all()

    return req_products


@router.get('/detail/{product_slug')
async def product_detail(db: Annotated[Session, Depends(get_db)], product_slug: str):
    product = db.scalar(select(Product).filter(Product.slug == product_slug))

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no product',
        )
    return product


@router.put('/detail/{product_slug')
async def update_product(db: Annotated[Session, Depends(get_db)], product_slug: str, update_product: CreateProduct):
    product = db.scalar(select(Product).where(Product.slug == product_slug))
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no product found',
        )
    db.execute(update(Product).where(Product.slug == product_slug).values(name=update_product.name,
                                                                          slug=slugify(update_product.name),
                                                                          description=update_product.description,
                                                                          price=update_product.price,
                                                                          image_url=update_product.image_url,
                                                                          stock=update_product.stock,
                                                                          category_id=update_product.category,
                                                                          rating=0.0,
                                                                          ))
    db.commit()
    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Product update is successful',
    }


@router.delete('/delete')
async def delete_product(db: Annotated[Session, Depends(get_db)], product_id: int):
    product = db.scalar(select(Product).filter(Product.id == product_id))

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no product found',
        )

    db.execute(update(Product).where(Product.id == product_id).values(is_active=False))
    db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Product delete is successful'
    }
