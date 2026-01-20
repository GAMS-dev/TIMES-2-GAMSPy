## TIMES Demo model

This is a demo model presenting the use of the TIMES model generator.

The demo model (the GAMS input data files specifying the model) is in the subfolder Model.
All the input data files are text files, usually generated from a database by a user shell,
but they can also be created and edited with any text editor.

The TIMES source code is in the subfolder ```source``` (licensed under GPLv3).<br>
The TIMES_Demo model data is in the subfolders ```model``` and ```model-ge``` (licensed under CC-BY-4.0).

You can run the model with GAMS in the Model subfolder, using the following command:
>  GAMS rundemo

This demo model is based on the Demo12 model documented in the TIMES documentation available on the ETSAP site [TIMES Documentation Part IV](https://iea-etsap.org/docs/TIMES%20Documentation%20PART%20IV_final.pdf)
and on GitHub [TIMES_Documentation](https://github.com/etsap-TIMES/TIMES_Documentation).

The demo model runs using the [CBC solver](https://github.com/coin-or/Cbc) which is an open-source mixed integer programming
solver working with the COIN-OR LP solver CLP and the COIN-OR Cut generator library Cgl.
