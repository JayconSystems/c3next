from setuptools import setup, find_packages

setup (name = 'c3next',
       version = '1.5.3',
       packages=find_packages(where="src"),
       package_dir={"": "src"},
       author = "C3 Wireless",
       author_email = "info@c3wireless.com",
       license = None,
       zip_safe = True,
       tests_require=['pytest'],
       install_requires=['klein','alchimia','psycopg2cffi',
                         'pycryptodome','jinja2','pytz','alembic',
                         'six', 'enum-compat'],
       package_data={
           '': ['*.html','*.png','*.jpg','*.js']
       }
)
