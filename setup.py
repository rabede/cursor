from setuptools import setup, find_packages

setup(
    name="library-search-tool",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests==2.31.0",
        "beautifulsoup4==4.12.2",
        "selenium==4.18.1",
        "fastapi==0.110.0",
        "uvicorn==0.27.1",
        "python-dotenv==1.0.1",
        "sqlalchemy==2.0.27",
        "pydantic==2.6.1",
        "pytest==8.0.0",
    ],
    python_requires=">=3.8",
) 