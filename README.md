
# PhD Tracker

### QA Deployment Status  
[![Deploy PhDTracker App Staging](https://github.com/Exitare/PhD-Tracker/actions/workflows/staging_deploy.yml/badge.svg)](https://github.com/Exitare/PhD-Tracker/actions/workflows/staging_deploy.yml)

### Live Deployment Status   
[![Deploy PhDTracker App Production](https://github.com/Exitare/PhD-Tracker/actions/workflows/prod_deploy.yml/badge.svg)](https://github.com/Exitare/PhD-Tracker/actions/workflows/prod_deploy.yml)


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