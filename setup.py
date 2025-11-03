from setuptools import setup, find_packages

setup(
    name="inventory_optimizer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'Flask==2.0.3',
        'pandas==1.4.4',
        'numpy==1.22.4',
        'matplotlib==3.5.3',
        'python-dateutil==2.8.2',
        'pytz==2023.3',
        'Werkzeug==2.0.3',
        'Jinja2==3.0.3',
        'MarkupSafe==2.0.1',
        'click==8.0.4',
        'itsdangerous==2.1.2',
        'gunicorn==20.1.0'
    ],
    python_requires='>=3.8,<3.11',
)
