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
    subcategories = db.scalars(select(Category).where(Category.parent_id == category.id))
    requried_category_id = [s.id for s in subcategories.all()]
    requried_category_id.append(category.id)

    req_products = db.scalars(select(Product).filter(Product.category_id.in_(requried_category_id), Product.stock > 0, Product.is_active == True)).all()

    return req_products


@router.get('/detail/{product_slug')
async def product_detail(product_slug: str):
    pass


@router.put('/detail/{product_slug')
async def update_product(product_slug: str):
    pass


@router.delete('/delete')
async def delete_product(product_id: int):
    pass
