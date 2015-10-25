# stubgen
stubgen generates C source from object file contains DWARF debugging information

# Requirements
List of packages that must be installed to build this software:

* pip
* virtualenv

To install the packages:

    $ sudo apt-get install python-pip 
    $ sudo pip install virtualenv

To install virtual development environment:

	$ sudo scripts/prerequisites.sh

# Development
To activte the virtual development environment:

	$ source venv/bin/activate

To see build commands:

    $ make help

To run test suites:

    $ make test

