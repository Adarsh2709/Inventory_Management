from setuptools import setup, find_packages

setup(
    name="inventory_optimizer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'Flask==2.3.3',
        'pandas==1.5.3',
        'numpy==1.24.3',
        'matplotlib==3.7.2',
        'python-dateutil==2.8.2',
        'pytz==2023.3',
        'Werkzeug==2.3.7',
        'Jinja2==3.1.2',
        'MarkupSafe==2.1.3',
        'click==8.1.6',
        'itsdangerous==2.1.2',
        'gunicorn==21.2.0'
    ],
    python_requires='>=3.8,<3.12',
)
