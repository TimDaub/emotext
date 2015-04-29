# Emotext
Emotext is framework that helps you extract, save and correlate emotions with contextual information.
It uses MIT's conceptnet5, nltk and Python.

To enable programming-language-independent usage, Emotext's interface is provided RESTfully.

## Automatic installation
Emotext uses `pip` for dependency management. To install all required dependencies, you simply run:

    pip install -r requirements.txt

Additionally, you'll need to download `nltk`'s [language-specific files](#downloading-nltks-language-specific-files).

## Manual installation
Python3 is required, as well as `pip` for installing dependencies.
The web server is hosted using `flask`. Tests are implemented against the RESTful interface, therefore the `requests` library is required.

    pip install flask
    pip install requests

Furthermore, `ntlk` is used for natural language processing. It can also be installed using `pip`:

    pip install nltk

However, `ntlk` still needs [language-specific files](#downloading-nltks-language-specific-files).

## Downloading nltk's language-specific files
Enter Python's IDE by typing `python` in your terminal and run the following commands: 

    >>> import nltk
    >>> nltk.download()

We recommend downloading all dependencies.

## Setting up a local Conceptnet image
As mentioned already, Emotext is able to extract emotions from text. This is done by looking up concepts on conceptnet5's graph database.
Through path finding, emotext searches an arbitrary number of levels for connections to find a connection between the entered word and an emotion.
This process requires *a lot* of lookups, which is why we recommend hosting a local instance of conceptnet5 instead of using the web-API.

A detailed installation tutorial on how to set up docker and conceptnet5 can be found [here](https://github.com/commonsense/conceptnet5/wiki/Docker).
However, we will still go through the installation process here:

1. [Install docker (Mac OS X)](https://docs.docker.com/installation/mac/). Make sure, that you're using a bash shell, otherwise the installation will probably fail at some point.
2. [Increase your virtual machine's HD](https://docs.docker.com/articles/b2d_volume_resize/) up to 100-150 GB of storage.
3. Pull conceptnet5-web from docker's repositories: `sudo docker run rspeer/conceptnet-web:5.3`
4. In your VirtualBox GUI, setup a port forward from port 80 of your virtual machine to port 80 of your real machine (NAT Interface in the tab "Network")
5. Run the application with a port forward from 10053 to 80, like this: 
`docker run -it -p 80:10053 rspeer/conceptnet-web --net=host`
6. Now, do either `boot2docker ip` or `arp -an` to find your virtual machine's ip
7. Once you were able to find the right IP, conceptnet5's web interface should appear, if you enter it in your browser

## Configuration
For convenience, when wanting to adjust parameters concerning for example the emotion extraction process there is the file `config.cfg`.
After changes on this file, the server must be restarted.

If you want to connect to the docker container's shell, try:
`sudo docker exec -i -t <containerID> bash`.

### Removing conceptnet5's request limiter
Per default, conceptnet5 limits requests to about 6000 in 60 minutes (https://github.com/commonsense/conceptnet5/search?utf8=%E2%9C%93&q=Limiter).
To remove the limiter, open the docker container's bash (as described above) and `cd conceptnet5`. Install `apt-get install nano` and `nano api.py`.
Inside of this file `Limiter` gets exported and an instance of it is assigned to `limiter`. Also python-decorators `@limiter` are used to limit conceptnet5's requests. You have to remove all of them.





