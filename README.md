




## Alembic

Apply Migrations (When Needed)

To apply new changes later:
```alembic upgrade head```


 Make Future Schema Changes with Alembic

Whenever you update your models:
```alembic revision --autogenerate -m "Add X table / Modify Y column"```
```alembic upgrade head```


To recreate schema:
```alembic upgrade head```