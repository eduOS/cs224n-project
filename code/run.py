import tensorflow as tf
import numpy as np
import sys, os, time, pickle
from similarity_model import SimilarityModel

TRAIN_DATA_PATH = "../data/quora/train.tsv"
TEST_DATA_PATH = "../data/quora/test.tsv"
GLOVE_VECTORS_PATH = "../data/glove/glove.6B.200d.npy"
TOKENS_TO_INDEX_PATH = "../data/glove/glove.6B.200d.pkl"
MAX_LENGTH_PATH = "../data/quora/max_length.pkl"

class Config:
    """Holds model hyperparams and data information.

    The config class is used to store various hyperparameters and dataset
    information parameters. Model objects are passed a Config() object at
    instantiation.
    """
    # each word just indexes into glove vectors
    n_features = 1
    n_classes = 2
    dropout = 0.5
    # word vector dimensions
    embed_size = 50
    hidden_size = 300
    batch_size = 32
    n_epochs = 10
    max_grad_norm = 10.
    lr = 0.001

def normalize(word):
    """
    Normalize words that are numbers or have casing.
    """
    if word.isdigit(): return NUM
    else: return word.lower()

def read_datafile(fstream):
    """
    Reads a input stream @fstream (e.g. output of `open(fname, 'r')`) in TSV file format.
    Input file is formatted as follows:
        QUESTION1
        QUESTION2
        LABEL
        ...
    where QUESTION1 and QUESTION2 are tab-delimited strings, and LABEL is an int.

    @returns a list of examples [([sentence1, sentence2], label)].
        @sentence1 and @sentence2 are lists of strings, @label is a boolean
    """
    examples = []
    sentence1 = sentence2 = label = None

    for line_num, line in enumerate(fstream):
        line = line.strip()
        if line_num % 3 == 0:
            sentence1 = line.split("\t")
        elif line_num % 3 == 1:
            sentence2 = line.split("\t")
        else:
            label = int(line)
            examples.append(([sentence1, sentence2], label))

    return examples

def load_and_preprocess_data(train_file_path, dev_file_path, tokens_to_glove_index_path, max_length_path):
    """
    Reads the training and dev data sets from the given paths.
    TODO: should we have train/validation/test split instead of just train/dev?
    """
    print "Loading training data..."
    with open(train_file_path) as train_file:
        train = read_datafile(train_file)
    print "Done. Read %d sentences" % len(train)
    print "Loading dev data..."
    with open(dev_file_path) as dev_file:
        dev = read_datafile(dev_file)
    print "Done. Read %d sentences"% len(dev)

    # now process all the input data: turn words into the glove indices
    print "Converting words into glove vector indices..."
    helper = ModelHelper.load(tokens_to_glove_index_path, max_length_path)
    train_data = helper.vectorize(train)
    dev_data = helper.vectorize(dev)

    return helper, train_data, dev_data, train, dev

class ModelHelper(object):
    """
    This helper takes care of preprocessing data, constructing embeddings, etc.
    """
    def __init__(self, tok2id, max_length):
        self.tok2id = tok2id
        self.UNKNOWN_WORD_INDEX = len(tok2id)
        self.PADDING_WORD_INDEX = len(tok2id) + 1
        # TODO: If we can have different amounts of padding for training vs. testing data,
        # then we can just compute the max_length in the vectorize functions.
        # Otherwise, we should load in max_length from some saved PKL file
        self.max_length = max_length

    # add additional embeddings for unknown word and padding word 
    def add_additional_embeddings(self, embeddings):
        '''Creates additional embeddings for unknown words and the padding word
        Returns a (2, embed_size) numpy array:
        - 0th row is word vector for unknown word, average of some known words
        - 1st row is word vector for padding word, all zeros
        '''
        unknown_word_vector = np.mean(embeddings[:100, :], axis=0) # vector for unknown word
        padding_word_vector = np.zeros(embeddings.shape[1])
        self.additional_embeddings = np.stack([unknown_word_vector, padding_word_vector])

    def vectorize_sentences(self, sentences):
        sentence1 = [self.tok2id.get(word, self.UNKNOWN_WORD_INDEX) for word in sentences[0]]
        sentence2 = [self.tok2id.get(word, self.UNKNOWN_WORD_INDEX) for word in sentences[1]]
        return [sentence1, sentence2]

    def vectorize(self, data):
        return [(self.vectorize_sentences(sentences), labels) for sentences, labels in data]

    @classmethod
    def load(cls, tokens_to_glove_index_path, max_length_path):
        # Make sure the directory exists.
        assert os.path.exists(tokens_to_glove_index_path)
        with open(tokens_to_glove_index_path, 'rb') as f:
            tok2id = pickle.load(f)
        with open(max_length_path, 'rb') as f:
            max_length = pickle.load(f)
        return cls(tok2id, max_length)


if __name__ == "__main__":
    print "Preparing data..."
    config = Config()
    helper, train, dev, train_raw, dev_raw = load_and_preprocess_data(TRAIN_DATA_PATH, TEST_DATA_PATH, TOKENS_TO_INDEX_PATH, MAX_LENGTH_PATH)
    print train_raw[0]
    print dev_raw[0]
    print train[0]
    print dev[0]
    
    print "Load embeddings..."
    embeddings = np.load(GLOVE_VECTORS_PATH, mmap_mode='r')
    config.embed_size = embeddings.shape[1]
    print config.embed_size

    # append unknown word and padding word vectors
    helper.add_additional_embeddings(embeddings)




    with tf.Graph(    ).as_default():
    #     logger.info("Building model...",)
    #     start = time.time()
    #     model = RNNModel(helper, config, embeddings)
    #     logger.info("took %.2f seconds", time.time() - start)
        print "Building model..."
        start = time.time()
        model = SimilarityModel(helper, config, embeddings)
        print "took %.2f seconds" % (time.time() - start)

        init = tf.global_variables_initializer()
        saver = None

        with tf.Session() as session:
            session.run(init)
            model.fit(session, saver, train, dev)

    # logger.info("Model did not crash!")
    # logger.info("Passed!")
