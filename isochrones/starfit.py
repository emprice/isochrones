import matplotlib.pyplot as plt

import os, os.path, re, sys
import logging
import time

from configobj import ConfigObj
from .starmodel import StarModel


def initLogging(filename, logger):
    if logger == None:
        logger = logging.getLogger()
    else:  # wish there was a logger.close()
        for handler in logger.handlers[:]:  # make a copy of the list
            logger.removeHandler(handler)

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt='%(asctime)s: %(message)s')

    fh = logging.FileHandler(filename)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    logger.addHandler(sh)
    return logger

def get_ichrone(models):
    if models=='dartmouth':
        from isochrones.dartmouth import Dartmouth_Isochrone
        ichrone = Dartmouth_Isochrone()
    elif models=='padova':
        from isochrones.padova import Padova_Isochrone
        ichrone = Padova_Isochrone()
    elif models=='basti':
        from isochrones.basti import Basti_Isochrone
        ichrone = Basti_Isochrone()
    else:
        raise ValueError('Unknown stellar models: {}'.format(args.models))

def starfit(folder, multiplicities=['single'], ichrone=None, models='dartmouth',
            use_emcee=False, plot_only=False, overwrite=False, verbose=False,
            logger=None):
    """ Runs starfit routine for a given folder.
    """
    nstars = {'single':1,
              'binary':2,
              'triple':3}

    if ichrone is None:
        ichrone = get_ichrone(models)

    for mult in multiplicities:
        print('{} starfit...'.format(mult))
        model_filename = '{}_starmodel_{}.h5'.format(models, mult)

        #initialize logger for folder
        logfile = os.path.join(folder, 'starfit.log')
        logger = initLogging(logfile, logger)

        name = os.path.basename(os.path.abspath(folder))

        try:
            start = time.time()
            if plot_only:
                try:
                    mod = StarModel.load_hdf('{}/{}'.format(folder,model_filename), 
                                           name=name)
                except:
                    pass
            else:
                # Only try to fit model if it doesn't exist, unless overwrite is set
                fit_model = True
                
                try:
                    mod = StarModel.load_hdf('{}/{}'.format(folder,model_filename), 
                                         name=name)
                    fit_model = False
                except:
                    pass

                if fit_model or overwrite:
                    ini_file = os.path.join(folder, 'star.ini')
                    c = ConfigObj(ini_file)
                    N = nstars[mult] if 'N' not in c else None

                    mod = StarModel.from_ini(ichrone, folder, use_emcee=use_emcee, N=N)
                    try:
                        mod.obs.print_ascii()
                    except:
                        pass

                    mod.fit(verbose=verbose, overwrite=overwrite)

                    mod.save_hdf(os.path.join(folder, model_filename))
                else:
                    logger.info('{} exists.  Use -o to overwrite.'.format(model_filename))

            # Only make corner plots if they are older 
            #  than the starmodel hdf file
            make_corners = False
            for x in ['physical', 'observed']:
                f = os.path.join(folder, 
                                 '{}_corner_{}_{}.png'.format(models, mult, x))
                if not os.path.exists(f):
                    make_corners = True
                    break
                else:
                    t_mod = os.path.getmtime(os.path.join(folder,model_filename))
                    t_plot = os.path.getmtime(f)
                    if t_mod > t_plot:
                        make_corners=True

            if make_corners or plot_only:
                corner_base = os.path.join(folder, '{}_corner_{}'.format(models, mult))
                fig1,fig2 = mod.corner_plots(corner_base)


            # Make mag plot if necessary.
            magplot_file = os.path.join(folder, '{}_mags_{}.png'.format(models, mult))
            make_magplot = False #True
            if os.path.exists(magplot_file):
                if os.path.getmtime(os.path.join(folder, model_filename)) > \
                        os.path.getmtime(magplot_file) or \
                        plot_only:
                    pass
                else:
                    make_magplot = False

            if make_magplot:
                fig = mod.mag_plot()
                plt.savefig(os.path.join(folder,'{}_mags_{}.png'.format(models, mult)))
                
            end = time.time()
            if plot_only:
                logger.info('{} starfit successful (plots only) for '.format(mult) +
                            '{} in {:.1f} minutes.'.format(folder, (end-start)/60))
            else:
                logger.info('{} starfit successful for '.format(mult) +
                            '{} in {:.1f} minutes.'.format(folder, (end-start)/60))
        except KeyboardInterrupt:
            logger.error('{} starfit calculation interrupted for {}.'.format(mult,folder))
            raise
        except:
            logger.error('{} starfit calculation failed for {}.'.format(mult,folder),
                         exc_info=True)

    return logger