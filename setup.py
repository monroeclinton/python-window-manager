from setuptools import setup

setup(
    name='python-window-manager',
    version='0.1',
    description='Example window manager.',
    license='MIT',
    url='http://github.com/monroeclinton/python-window-manager',
    author='Monroe Clinton',
    scripts=['run_pwm'],
    install_requires=[
        'pyyaml',
        'xcffib==0.11.1',
        'xpybutil==0.0.6',
    ],
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
    ],
    python_requires='>=3.6',
)
