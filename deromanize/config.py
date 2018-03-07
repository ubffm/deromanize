from pathlib import Path
from . import KeyGenerator

try:
    import yaml
except ImportError:
    yaml = None

CFG_PATHS = [Path()/'.deromanize.yml',
             Path.home()/'.config'/'derom'/'config.yml']
PROJ_PATH = Path(__file__).parents[1]


class ConfigError:
    pass


class Config:
    def __init__(self, path=None, loader=None):
        self.path = path
        self.loader = loader or (lambda path: yaml.safe_load(open(str(path))))
        self.user_conf = self.find_configs()
        self.schemas = get_schemas(self.user_conf)

    def from_schema(self, schema_name, *args, **kwargs):
        return KeyGenerator(self.get_profile(schema_name),
                            *args, **kwargs)

    def get_profile(self, schema_name):
        return self.loader(self.schemas[schema_name])

    def find_configs(self):
        """locate the yaml config file and return it deserialized."""
        if self.path:
            path = Path(self.path)
        else:
            for path in CFG_PATHS:
                if path.exists():
                    break
            else:
                return {}
        return self.loader(path)

    def __getitem__(self, key):
        return self.user_conf[key]


def get_schemas(user_conf: dict):
    u_schemas = user_conf.get('schemas')
    if u_schemas is None:
        schema_paths = (PROJ_PATH/'data').glob('*.yml')
    elif isinstance(u_schemas, list):
        schema_paths = map(Path, u_schemas)
    elif u_schemas.endswith('.yml'):
        schema_paths = [Path(u_schemas)]
    else:
        schema_paths = Path(u_schemas).glob('*.yml')

    return {p.stem: p for p in schema_paths}
