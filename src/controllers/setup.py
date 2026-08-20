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
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hector-la',
    maintainer_email='hectorla@espol.edu.ec',
    description='Control nodes for the AutoDRIVE F1TENTH vehicle (labs/tutorials)',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop_hold = controllers.teleop_hold:main',
            'gap_node = controllers.gap_node:main',
        ],
    },
)
