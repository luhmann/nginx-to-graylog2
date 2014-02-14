nginx-to-graylog2-myvideo
=========================

An nginx logfile-parser that pushes messages to graylog2 by using [graypy](https://pypi.python.org/pypi/graypy). 
We look for a special form within the entry that contains information about Javascript Application Errors and 
push them to a standard [Graylog2-Instance](https://pypi.python.org/pypi/graypy) that is assumed to run 
at the standard location

### Dependencies
* [graypy ~0.2.9](https://pypi.python.org/pypi/graypy/0.2.9)
* [user-agents ~0.2.0](https://pypi.python.org/pypi/user-agents/)
* [python-argparse ~2.7](http://docs.python.org/2/library/argparse.html)
* [python-dateutil ~2.2](https://pypi.python.org/pypi/python-dateutil)
