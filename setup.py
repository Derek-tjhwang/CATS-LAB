from setuptools import setup, find_packages

setup(name='coza',
      version='0.2',
      description='Crypto currency trading framework',
      url='',
      author='Tae-jun Hwang',
      author_email='derek.tjhwang@gmail.com',
      license='GPL3',
      packages=find_packages(),
      install_requires=[
          'requests==2.20.0',
          'numpy==1.14.0',
          'pandas==0.20.3',
          'APScheduler==3.5.1',
          'beautifultable==0.5.2',
          'plotly==3.4.2',
          'fake_useragent==0.1.11',
      ],
      zip_safe=False)
