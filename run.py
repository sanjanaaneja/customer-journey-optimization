# Run the full analysis pipeline
import os, sys
root = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(root, 'src'))
os.makedirs(os.path.join(root, 'data'), exist_ok=True)
os.makedirs(os.path.join(root, 'outputs', 'figures'), exist_ok=True)
exec(open('generate_data.py').read())
exec(open('analyze.py').read())
