from setuptools import setup

setup(
    name='miditoolkit',
    version='0.1.2',
    description='toolkit for midi/piano-roll manipulation, conversion and visualization.',
    author='Wen-Yi Hsiao',
    author_email='s101062219@gmail.com',
    url='https://github.com/wayne391/miditoolkit',
    packages=['miditoolkit'],
    classifiers=[
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
    ],
    keywords='midi piano-roll music',
    license='MIT',
    install_requires=[
        'mido',
        'matplotlib',
        'numpy',
        'scipy'
    ]
)