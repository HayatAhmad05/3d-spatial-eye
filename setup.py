"""
Setup script for 3D Spatial Eye package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="3d-spatial-eye",
    version="1.0.0",
    author="Sayed",
    description="Real-time 3D point cloud scanner for Raspberry Pi 5",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HayatAhmad05/3d-spatial-eye",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Hardware",
    ],
    python_requires=">=3.9",
    install_requires=[
        "flask>=3.0",
        "flask-socketio>=5.3",
        "python-socketio>=5.10",
        "numpy>=1.26",
    ],
    extras_require={
        "pi": [
            "vl53l1x>=0.0.5",
            "gpiozero>=2.0",
            "pigpio>=1.78",
            "RPi.GPIO>=0.7.1",
            "smbus2>=0.4.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "spatial-eye=pi_scanner.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "pi_scanner": [
            "web/templates/*.html",
            "web/static/*.css",
            "web/static/*.js",
        ],
    },
)
