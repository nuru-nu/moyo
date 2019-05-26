"""Contains functions for generating and using equal-loudness contours for
side-presented steady pure tones according to the ISO/IEC 226 standard.
 
"""
 
 
__author__ = 'Sam Mathias'
__version__ = 1.0
 
 
import numpy as np
from scipy.interpolate import interp1d
 
 
def iso266(phon, return_freq=False):
    """Returns an equal-loudness contour evaluated at 29 frequencies between
    20 Hz and 12.5 kHz according to the ISO/IEC 226 standard [1]_.
 
    Parameters
    ----------
    phon : int or float
        The phon value represented by the equal-loudness contour, where a value
        of :math:`x` phon is the loudness of 1-KHz steady pure tone presented
        at :math:`x` dB SPL. Must be between 0 and 90.
    return_freq : bool, optional
        If True, the function returns the frequency values as well as the SPL
        values of the contour. Default is False.
 
    Returns
    -------
    array_like
        Either a 1-D or a 2-D numpy array, depending on `return_freq`.
 
    Reference
    ---------
    .. [1] ISO/IEC (2003). ISO/IEC 226:2003 Acoustics -- Normal equal-loudness-
       level contours.
       http://www.iso.org/iso/catalogue_detail.htm?csnumber=34222.
 
    Example
    -------
    >>> elc = iso266(60, return_freq=True)
    >>> print elc
    [[    20.             25.             31.5            40.             50.
          63.             80.            100.            125.            160.
         200.            250.            315.            400.            500.
         630.            800.           1000.           1250.           1600.
        2000.           2500.           3150.           4000.           5000.
        6300.           8000.          10000.          12500.        ]
     [   109.51132227    104.22789784     99.07786826     94.17731862
          89.96345731     85.94342131     82.05340072     78.65461863
          75.56345314     72.4743448      69.86431929     67.53483532
          65.39173983     63.45099627     62.0511792      60.81495942
          59.88668375     60.011588       62.1549143      63.18935604
          59.96161453     57.25515019     56.42385863     57.56993838
          60.8882125      66.36125056     71.66396598     73.15510401
          68.63077045]]
 
    """
    if not 0 <= phon <= 90:
        raise ValueError('Cannot calculate for this value.')
 
    f = np.array([
        20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500,
        630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000,
        10000, 12500
    ])
 
    af = np.array([
        0.532, 0.506, 0.480, 0.455, 0.432, 0.409, 0.387, 0.367, 0.349, 0.330,
        0.315, 0.301, 0.288, 0.276, 0.267, 0.259, 0.253, 0.250, 0.246, 0.244,
        0.243, 0.243, 0.243, 0.242, 0.242, 0.245, 0.254, 0.271, 0.301
    ])
 
    Lu = np.array([
        -31.6, -27.2, -23.0, -19.1, -15.9, -13.0, -10.3, -8.1, -6.2, -4.5,
        -3.1, -2.0, -1.1, -0.4, 0.0, 0.3, 0.5, 0.0, -2.7, -4.1, -1.0,  1.7,
        2.5, 1.2, -2.1, -7.1, -11.2, -10.7, -3.1
    ])
 
    Tf = np.array([
        78.5, 68.7, 59.5, 51.1, 44.0, 37.5, 31.5, 26.5, 22.1, 17.9, 14.4, 11.4,
        8.6, 6.2, 4.4, 3.0, 2.2, 2.4, 3.5, 1.7, -1.3, -4.2, -6.0, -5.4, -1.5,
        6.0, 12.6, 13.9, 12.3
    ])
 
    Ln = phon
 
    Af = 4.47e-3 * (10 ** (.025 * Ln) - 1.15) \
         + (.4 * 10 ** (((Tf + Lu) / 10.) - 9)) ** af
    Lp = ((10 / af) * np.log10(Af)) - Lu + 94
 
    spl = Lp
    freq = f
 
    if return_freq is True:
        return np.array([freq, spl])
     
    else:
        return spl
 
 
def equal_loudness(phon, freqs, return_freq=False):
    """Returns equal-loudness levels for any frequencies between 20 Hz and
    12.5 kHz according to the ISO/IEC 226 standard [1]_.
 
    Parameters
    ----------
    phon : number
        The phon value represented by the equal-loudness contour, where a value
        of :math:`x` phon is the loudness of 1-KHz steady pure tone presented
        at :math:`x` dB SPL. Must be between 0 and 90.
    freqs : number or array_like
        Frequency or frequencies in Hz to be evaluated. Must be between 20 and
        12500.
    return_freq : bool, optional
        If True, the function returns the frequency values as well as the SPL
        values of the contour. Default is False.
 
    Returns
    -------
    array_like
        Either a 1-D or a 2-D numpy array, depending on `return_freq`.
 
    Reference
    ---------
    .. [1] ISO/IEC (2003). ISO/IEC 226:2003 Acoustics -- Normal equal-loudness-
       level contours.
       http://www.iso.org/iso/catalogue_detail.htm?csnumber=34222.
 
    Example
    -------
    >>> el = equal_loudness(60, [500, 1000, 2000], return_freq=True)
    >>> print el
    [[  500.          1000.          2000.        ]
     [   62.0511792     60.011588      59.96161453]]
 
    """
    f = interp1d(*iso266(phon, True), kind='cubic')
     
    if return_freq is True:
        return np.array([freqs, f(freqs)])
     
    else:
        return f(freqs)
 
 
def get_loudness(spl, freq):
    """Returns the approximate loudness level in phons for a side-presented
    steady pure tone according to the ISO/IEC 226 standard [1]_.
 
    This function generates a range of equal-loudness contours and interpolates
    between them. Therefore it is more efficient to pass many level and
    frequency values to one function call than it is to make many function
    calls.
 
    Parameters
    ----------
    spl : number or array_like
        Sound pressure level or levels in dB SPL.
    freq : number or array_like
        Frequency or frequencies in Hz.
 
    Returns
    -------
    number or array_like
        Phon value(s).
 
    Reference
    ---------
    .. [1] ISO/IEC (2003). ISO/IEC 226:2003 Acoustics -- Normal equal-loudness-
       level contours.
       http://www.iso.org/iso/catalogue_detail.htm?csnumber=34222.
 
    Example
    -------
    >>> phons = get_loudness([50, 60, 70] [500, 500, 500])
    >>> print phons
    [ 47.3  57.8  68.4]
     
    """
    phons = np.arange(0, 90.1, .1)
    freqs = np.arange(20, 12501)
    spls = np.empty((len(phons), len(freqs)))
 
    for i, phon in enumerate(phons):
        spls[i] = equal_loudness(phon, freqs)
 
    if not hasattr(spl, '__iter__'):
        spl = [spl]
 
    if not hasattr(freq, '__iter__'):
        freq = [freq]
 
    spls = spls.T
    results = []
     
    for _spl, _freq in zip(spl, freq):
        ix = (np.abs(freqs - _freq)).argmin()
        iy = (np.abs(spls[ix] - _spl)).argmin()
        results.append(phons[iy])
 
    if len(results) == 1:
        return results[0]
 
    else:
        return np.array(results)
 
 
if __name__ == '__main__':
    pass