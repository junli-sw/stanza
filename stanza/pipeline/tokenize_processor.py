"""
Processor for performing tokenization
"""

import io
import logging

from stanza.models.tokenization.data import DataLoader
from stanza.models.tokenization.trainer import Trainer
from stanza.models.tokenization.utils import output_predictions
from stanza.pipeline._constants import *
from stanza.pipeline.processor import UDProcessor, register_processor
from stanza.pipeline.registry import PROCESSOR_VARIANTS
from stanza.utils.datasets.postprocess_vietnamese_tokenizer_data import paras_to_chunks
from stanza.models.common import doc
from stanza.pipeline.external.jieba import JiebaTokenizer
from stanza.pipeline.external.spacy import SpacyTokenizer
from stanza.pipeline.external.sudachipy import SudachiPyTokenizer
from stanza.pipeline.external.pythainlp import PyThaiNLPTokenizer

from stanza.models.tokenization.torch_data import DocsDataset
from torch.utils.data import DataLoader as TorchDataLoader
from torch.autograd import Variable
from stanza.models.tokenization.torch_data import transform
from tqdm import tqdm
import numpy as np
import torch

logger = logging.getLogger('stanza')

# class for running the tokenizer
@register_processor(name=TOKENIZE)
class TokenizeProcessor(UDProcessor):

    # set of processor requirements this processor fulfills
    PROVIDES_DEFAULT = set([TOKENIZE])
    # set of processor requirements for this processor
    REQUIRES_DEFAULT = set([])
    # default max sequence length
    MAX_SEQ_LENGTH_DEFAULT = 1000

    def _set_up_model(self, config, use_gpu):
        # set up trainer
        if config.get('pretokenized'):
            self._trainer = None
        else:
            self._trainer = Trainer(model_file=config['model_path'], use_cuda=use_gpu)

    def process_pre_tokenized_text(self, input_src):
        """
        Pretokenized text can be provided in 2 manners:

        1.) str, tokenized by whitespace, sentence split by newline
        2.) list of token lists, each token list represents a sentence

        generate dictionary data structure
        """

        document = []
        if isinstance(input_src, str):
            sentences = [sent.strip().split() for sent in input_src.strip().split('\n') if len(sent.strip()) > 0]
        elif isinstance(input_src, list):
            sentences = input_src
        idx = 0
        for sentence in sentences:
            sent = []
            for token_id, token in enumerate(sentence):
                sent.append({doc.ID: (token_id + 1, ), doc.TEXT: token, doc.MISC: f'start_char={idx}|end_char={idx + len(token)}'})
                idx += len(token) + 1
            document.append(sent)
        raw_text = ' '.join([' '.join(sentence) for sentence in sentences])
        return raw_text, document

    def process(self, document):
        assert isinstance(document, str) or isinstance(document, doc.Document) or (self.config.get('pretokenized') or self.config.get('no_ssplit', False)), \
            "If neither 'pretokenized' or 'no_ssplit' option is enabled, the input to the TokenizerProcessor must be a string or a Document object."

        if isinstance(document, doc.Document):
            document = document.text

        if self.config.get('pretokenized'):
            raw_text, document = self.process_pre_tokenized_text(document)
        elif hasattr(self, '_variant'):
            return self._variant.process(document)
        else:
            raw_text = '\n\n'.join(document) if isinstance(document, list) else document
            # set up batches
            if self.config.get('lang') == 'vi':
                # special processing is due for Vietnamese
                text = '\n\n'.join([x for x in raw_text.split('\n\n')]).rstrip()
                dummy_labels = '\n\n'.join(['0' * len(x) for x in text.split('\n\n')])
                data = paras_to_chunks(text, dummy_labels)
                batches = DataLoader(self.config, input_data=data, vocab=self.vocab, evaluation=True)
            else:
                batches = DataLoader(self.config, input_text=raw_text, vocab=self.vocab, evaluation=True)
            # get dict data
            _, _, _, document = output_predictions(None, self.trainer, batches, self.vocab, None,
                                   self.config.get('max_seqlen', TokenizeProcessor.MAX_SEQ_LENGTH_DEFAULT),
                                   orig_text=raw_text,
                                   no_ssplit=self.config.get('no_ssplit', False))
        return doc.Document(document, raw_text)

    def bulk_process(self, docs, num_workers=8, batch_size=128):
        """
        A torch-based bulk-processing pipeline that uses torch dataloader and batch-wise inferencing.
        """

        """Create the dataset. Includes the transformation to prepare the text."""
        docs_dset = DocsDataset(docs=docs, transform=transform(self.config, self.vocab))

        """Build a DataLoader from it"""
        dloader = TorchDataLoader(docs_dset, batch_size=batch_size, num_workers=num_workers)

        self.trainer.model.eval()

        """Push each batch to GPU and perform a feed-forward push through the model"""
        for batch in tqdm(dloader):
            """One batch contains batch_size docs"""

            units_tensors = batch[0]
            features_tensors = batch[1]

            default_device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            units_tensors = Variable(units_tensors.cuda(default_device))
            features_tensors = Variable(features_tensors.cuda(default_device))

            _, predictions = torch.max(self.trainer.model(units_tensors, features_tensors), 1)
            predictions = predictions.cpu().tolist()
            #print(predictions)


        return []