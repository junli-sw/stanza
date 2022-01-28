from stanza.pipeline.core import Pipeline
from stanza.pipeline.multilingual import MultilingualPipeline
from stanza.models.common.doc import Document
from stanza.resources.common import download
from stanza.resources.installation import install_corenlp, download_corenlp_models
from stanza._version import __version__, __resources_version__
import os

import logging
logger = logging.getLogger('stanza')

# if the client application hasn't set the log level, we set it
# ourselves to INFO
if logger.level == 0:
    logger.setLevel(logging.INFO)

log_handler = logging.StreamHandler()
log_formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s",
                              datefmt='%Y-%m-%d %H:%M:%S')
log_handler.setFormatter(log_formatter)

# also, if the client hasn't added any handlers for this logger
# (or a default handler), we add a handler of our own
#
# client can later do
#   logger.removeHandler(stanza.log_handler)
if not logger.hasHandlers():
    logger.addHandler(log_handler)

proj_base = os.environ[ "TRAIN_PROJ_BASE"]
os.environ[ "UDBASE"] = f"{proj_base}/data/udbase"
os.environ[ "NERBASE" ] = f"{proj_base}/data/nerbase"
os.environ["DATA_ROOT"] = f"{proj_base}/data/processed"
os.environ[ "WORDVEC_DIR"] = f"{proj_base}/data/wordvec"

data_root = os.environ[ "DATA_ROOT"]
os.environ[ "TOKENIZE_DATA_DIR"] = f"{data_root}/tokenize"
os.environ["MWT_DATA_DIR"] = f"{data_root}/mwt"
os.environ["LEMMA_DATA_DIR"] = f"{data_root}/lemma"
os.environ["POS_DATA_DIR"] = f"{data_root}/pos"
os.environ[ "DEPPARSE_DATA_DIR"] = f"{data_root}/depparse"
os.environ[ "ETE_DATA_DIR"] = f"{data_root}/ete"

os.environ["NER_DATA_DIR"] = f"{data_root}/ner"
os.environ["CHARLM_DATA_DIR"] = f"{data_root}/charlm"

