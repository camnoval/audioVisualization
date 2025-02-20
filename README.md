# audioVisualization
Takes songs from yt, converts them to dominant frequency at each frame, then converts it to a specific color based on a logarithmic scaling from 4.00-7.00 which correspond to wavelengths 400-700 nm. Spits out a gradient of the entire song

Note that if you're going to run this, you need to run it in a virtual environment (venv) because the requirements are odd with moviepy? i believe. I know it's because of one of the libraries, but now I'm forgetting which one. Numpy needs to be below 2.1, so if you're running this and its not working, that's probably the problem.