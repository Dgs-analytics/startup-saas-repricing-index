from setuptools import find_packages, setup

setup(
    name="startup-saas-repricing-index",
    version="0.1.0",
    author="Dgs-analytics",
    description="Automated pipeline for tracking historical SaaS pricing page mutations via Wayback CDX API.",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "pandas>=2.0.0",
        "tqdm>=4.65.0",
        "urllib3>=2.0.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "plotly>=5.15.0",
        "beautifulsoup4>=4.12.0",
    ],
    python_requires=">=3.11",
)