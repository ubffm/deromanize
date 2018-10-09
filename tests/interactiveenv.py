import deromanize as dr
from deromanize import patterns
import yaml
with open('./tests/basic.yml') as fh:
    PROFILE = yaml.safe_load(fh)

small = dr.KeyGenerator(PROFILE.copy())
cfg = dr.Config()
new = cfg.from_schema('new')
