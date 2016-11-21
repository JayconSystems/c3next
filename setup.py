from setuptools import setup, find_packages

setup (name = 'c3next',
       version = '0.1.0',
       packages=find_packages(where="src"),
       package_dir={"": "src"},
       author = "C3 Wireless",
       author_email = "info@c3wireless.com",
       license = None,
       zip_safe = True,
       tests_require=['pytest'],
       install_requires=['klein','txacme','alchimia','psycopg2cffi',
                         'pycryptodome','jinja2'],
       package_data={
           '': ['*.html','*.png','*.jpg','*.js']
       }
)
