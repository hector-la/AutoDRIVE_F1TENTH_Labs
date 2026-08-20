import os
from glob import glob
from setuptools import find_packages, setup
package_name = 'global_planner'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'racelines'), glob('racelines/*.csv')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hector-la',
    maintainer_email='hectorla@espol.edu.ec',
    description='Parte B: planificación global (Dijkstra + Fem-pos) sobre el mapa de AutoDRIVE F1TENTH',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'raceline_publisher = global_planner.raceline_publisher:main',
        ],
    },
)
