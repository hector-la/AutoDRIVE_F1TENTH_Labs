import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'controllers'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hector-la',
    maintainer_email='hectorla@espol.edu.ec',
    description='F1TENTH lab controllers for the AutoDRIVE simulator',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gap_node = controllers.gap_node:main',
        ],
    },
)
