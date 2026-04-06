# style_config.py - chart styling for this project
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# clean white style with no top/right spines
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': 'lightgray',
    'axes.labelcolor': 'black',
    'text.color': 'black',
    'xtick.color': 'gray',
    'ytick.color': 'gray',
    'axes.grid': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
})

# matplotlib named colors - no custom hex codes
PRIMARY = 'midnightblue'
SECONDARY = 'steelblue'
TERTIARY = 'royalblue'
ACCENT = 'darkorange'
SUCCESS = 'seagreen'
DANGER = 'crimson'
WARNING = 'goldenrod'
MUTED = 'gray'
LIGHT = 'lightgray'
TEXT = 'black'
TEAL = 'teal'
PURPLE = 'rebeccapurple'

PALETTE = [ACCENT, PRIMARY, SECONDARY, PURPLE, TEAL, SUCCESS, DANGER, WARNING]
