!git clone https://github.com/Franck-Dernoncourt/pubmed-rct.git
!ls pubmed-rct

import tensorflow as tf

!ls "pubmed-rct/PubMed_20k_RCT_numbers_replaced_with_at_sign"

data_dir = "/content/pubmed-rct/PubMed_20k_RCT_numbers_replaced_with_at_sign/"

import os
filenames = [data_dir + filename for filename in os.listdir(data_dir)]
filenames

def get_lines(file_name):
  with open(file_name, 'r') as f:
    return f.readlines()

train_lines = get_lines(data_dir + "train.txt")
train_lines[:20]

def preprocess_text_with_line_numbers(file_name):
  input_lines = get_lines(file_name)
  abstract_lines = ""
  abstract_samples = []

  for line in input_lines:
    if line.startswith("###"):
      abstract_id = line
      abstract_lines = ""

    elif line.isspace():
      abstract_line_split = abstract_lines.splitlines()

      for abstract_line_number ,abstract_line in enumerate(abstract_line_split):
        line_data ={}
        target_text_split = abstract_line.split("\t")

        line_data['target'] = target_text_split[0]
        line_data['text'] = target_text_split[1].lower()
        line_data['line_number'] = abstract_line_number
        line_data['total_lines'] =  len(abstract_line_split) - 1

        abstract_samples.append(line_data)

    else:
      abstract_lines += line

  return abstract_samples

train_samples = preprocess_text_with_line_numbers(data_dir + "train.txt")
val_samples = preprocess_text_with_line_numbers(data_dir + "dev.txt")
test_samples = preprocess_text_with_line_numbers(data_dir + "test.txt")

val_samples[:10]

import pandas as pd
train_df = pd.DataFrame(train_samples)
val_df = pd.DataFrame(val_samples)
test_df = pd.DataFrame(test_samples)

train_df['target'].value_counts().plot(kind='bar')

# Convert abstract text lines into lists
train_sentences = train_df["text"].tolist()
val_sentences = val_df["text"].tolist()
test_sentences = test_df["text"].tolist()
len(train_sentences), len(val_sentences), len(test_sentences)

from sklearn.preprocessing import OneHotEncoder
one_hot_encoder = OneHotEncoder(sparse=False)
train_labels_one_hot = one_hot_encoder.fit_transform(train_df['target'].to_numpy().reshape(-1, 1))
val_labels_one_hot = one_hot_encoder.fit_transform(val_df['target'].to_numpy().reshape(-1, 1))
test_labels_one_hot = one_hot_encoder.fit_transform(test_df['target'].to_numpy().reshape(-1, 1))

from sklearn.preprocessing import LabelEncoder
label_encoder = LabelEncoder()
train_labels_encoded = label_encoder.fit_transform(train_df['target'].to_numpy().reshape(-1, 1))
val_labels_encoded = label_encoder.fit_transform(val_df['target'].to_numpy().reshape(-1, 1))
test_labels_encoded = label_encoder.fit_transform(test_df['target'].to_numpy().reshape(-1, 1))

num_classes = len(label_encoder.classes_)
class_names = label_encoder.classes_
num_classes, class_names

"""###CREATING OUR BASELINE MODEL"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# Create a TfidfVectorizer object
tfidf = TfidfVectorizer()

# Transform the email data into TF-IDF features
X = tfidf.fit_transform(train_df['text'])

baseline_model = MultinomialNB()
baseline_model.fit(X, train_labels_encoded)

train_labels_one_hot

# Make predictions on the test set
y_pred = baseline_model.predict(tfidf.transform(test_df['text']))

# Evaluate the model
print("Accuracy:", accuracy_score(test_labels_encoded, y_pred))
print("Confusion Matrix:\n", confusion_matrix(test_labels_encoded, y_pred))
print("Classification Report:\n", classification_report(test_labels_encoded, y_pred))

test_df['text']

!wget https://raw.githubusercontent.com/mrdbourke/tensorflow-deep-learning/main/extras/helper_functions.py
from helper_functions import calculate_results

len(val_labels_encoded), len(val_sentences)

y_pred = baseline_model.predict(tfidf.transform(val_sentences))

baseline_results = calculate_results(y_true=val_labels_encoded,
                                     y_pred=y_pred)
baseline_results

import tensorflow as tf
from tensorflow.keras import layers
import numpy as np

sent_lens = [len(sentence.split()) for sentence in train_sentences]
avg_sent_len = np.mean(sent_lens)
avg_sent_len, np.array(tf.reduce_max(sent_lens)) # return average sentence length (in tokens)

# What's the distribution look like?
import matplotlib.pyplot as plt
plt.hist(sent_lens, bins=7);

# How long of a sentence covers 95% of the lengths?
output_seq_len = int(np.percentile(sent_lens, 95))
output_seq_len

from tensorflow.keras.layers import TextVectorization

max_tokens = 68000

text_vectorizer = TextVectorization(max_tokens, output_sequence_length = output_seq_len)

text_vectorizer.adapt(train_sentences)

# How many words in our training vocabulary?
rct_20k_text_vocab = text_vectorizer.get_vocabulary()
print(f"Number of words in vocabulary: {len(rct_20k_text_vocab)}"),
print(f"Most common words in the vocabulary: {rct_20k_text_vocab[:5]}")
print(f"Least common words in the vocabulary: {rct_20k_text_vocab[-5:]}")

text_vectorizer.get_config()

from tensorflow.keras.layers import Embedding

embedding_layer = Embedding(64841, 128)

embedding_layer(text_vectorizer(train_sentences))

train_dataset = tf.data.Dataset.from_tensor_slices((train_sentences, train_labels_one_hot))
val_dataset = tf.data.Dataset.from_tensor_slices((val_sentences, val_labels_one_hot))
test_dataset = tf.data.Dataset.from_tensor_slices((test_sentences, test_labels_one_hot))

train_dataset = train_dataset.batch(32).prefetch(tf.data.AUTOTUNE)
val_dataset = val_dataset.batch(32).prefetch(tf.data.AUTOTUNE)
test_dataset = test_dataset.batch(32).prefetch(tf.data.AUTOTUNE)

"""CREATING A CONV1D MODEL"""

inputs = layers.Input(shape=(1,), dtype=tf.string)
x = text_vectorizer(inputs)
x = embedding_layer(x)
x = layers.Conv1D(64, (5))(x)
x = layers.Conv1D(32, (3))(x)
x = layers.GlobalAveragePooling1D()(x)
x = layers.Flatten()(x)
x = layers.Dense(32)(x)
x = layers.Activation('relu')(x)
x = layers.Dense(num_classes)(x)
outputs = layers.Activation('softmax')(x)

model_1 = tf.keras.Model(inputs, outputs)

model_1.compile(tf.keras.optimizers.Adam(),
                tf.keras.losses.CategoricalCrossentropy(),
                metrics=['accuracy'])

model_1.summary()

history_Conv1D_model_1 = model_1.fit((train_dataset), epochs=3, validation_data=val_dataset)

model_1_pred_probs = model_1.predict(test_dataset)

model_1_preds = class_names[tf.argmax(model_1_pred_probs, axis=1)]

results_model_1 = calculate_results(class_names[tf.argmax(test_labels_one_hot, axis=1)], model_1_preds)
results_model_1, baseline_results

import tensorflow_hub as hub
class EmbedLayer(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super(EmbedLayer, self).__init__(**kwargs)
        self.use_layer = hub.KerasLayer("https://tfhub.dev/google/universal-sentence-encoder/4",
                                        trainable=False,
                                        name='universal_sentence_encoder',
                                        dtype=tf.string,
                                        input_shape=[])
    def call(self, inputs):
        return self.use_layer(inputs)

"""Creating a model with pretrained backbone

"""

# Define feature extractor model using TF Hub layer
inputs = layers.Input(shape=[], dtype=tf.string)
x = EmbedLayer()(inputs) # tokenize text and create embedding
x = layers.Dense(128, activation="relu")(x) # add a fully connected layer on top of the embedding
# Note: you could add more layers here if you wanted to
outputs = layers.Dense(5, activation="softmax")(x) # create the output layer
model_2 = tf.keras.Model(inputs=inputs,
                        outputs=outputs)

# Compile the model
model_2.compile(loss="categorical_crossentropy",
                optimizer=tf.keras.optimizers.Adam(),
                metrics=["accuracy"])

import os
os.environ['TF_XLA_FLAGS'] = '--tf_xla_auto_jit=0'

history_use_model_2 = model_2.fit((train_dataset),steps_per_epoch=int(len(train_dataset) * 0.1), epochs=3, validation_data=val_dataset)

model_2.evaluate(val_dataset)

model_2_pred_probs = model_2.predict(test_dataset)
model_2_preds = class_names[tf.argmax(model_2_pred_probs, axis=1)]
results_model_2 = calculate_results(class_names[tf.argmax(test_labels_one_hot, axis=1)], model_2_preds)
results_model_2, baseline_results

import random
random_training_sentence = random.choice(train_sentences)

# Make function to split sentences into characters
def split_chars(text):
  return " ".join(list(text))

# Test splitting non-character-level sequence into characters
split_chars(random_training_sentence)

# Split sequence-level data splits into character-level data splits
train_chars = [split_chars(sentence) for sentence in train_sentences]
val_chars = [split_chars(sentence) for sentence in val_sentences]
test_chars = [split_chars(sentence) for sentence in test_sentences]
print(train_chars[0])

# What's the average character length?
char_lens = [len(sentence) for sentence in train_sentences]
mean_char_len = np.mean(char_lens)
mean_char_len

import matplotlib.pyplot as plt
plt.hist(char_lens, bins=7);

# Find what character length covers 95% of sequences
output_seq_char_len = int(np.percentile(char_lens, 95))
output_seq_char_len

import string
alphabet = string.ascii_lowercase + string.digits + string.punctuation
alphabet

# Create char-level token vectorizer instance
NUM_CHAR_TOKENS = len(alphabet) + 2 # num characters in alphabet + space + OOV token
char_vectorizer = TextVectorization(max_tokens=NUM_CHAR_TOKENS,
                                    output_sequence_length=output_seq_char_len,
                                    standardize="lower_and_strip_punctuation",
                                    name="char_vectorizer")

# Adapt character vectorizer to training characters
char_vectorizer.adapt(train_chars)

# Check character vocabulary characteristics
char_vocab = char_vectorizer.get_vocabulary()
print(f"Number of different characters in character vocab: {len(char_vocab)}")
print(f"5 most common characters: {char_vocab[:5]}")
print(f"5 least common characters: {char_vocab[-5:]}")

# Test out character vectorizer
random_train_chars = random.choice(train_chars)
print(f"Charified text:\n{random_train_chars}")
print(f"\nLength of chars: {len(random_train_chars.split())}")
vectorized_chars = char_vectorizer([random_train_chars])
print(f"\nVectorized chars:\n{vectorized_chars}")
print(f"\nLength of vectorized chars: {len(vectorized_chars[0])}")

char_embedding = tf.keras.layers.Embedding(NUM_CHAR_TOKENS,
                                           25,
                                           mask_zero=False,
                                           name="char_embed")

# Test out character embedding layer
print(f"Charified text (before vectorization and embedding):\n{random_train_chars}\n")
char_embed_example = char_embedding(char_vectorizer([random_train_chars]))
print(f"Embedded chars (after vectorization and embedding):\n{char_embed_example}\n")
print(f"Character embedding shape: {char_embed_example.shape}")

inputs = layers.Input((1, ), dtype=tf.string)
x = char_vectorizer(inputs)
x = char_embedding(x)
x = layers.Conv1D(64, 5, padding='same')(x)
x = layers.Activation('relu')(x)
x = layers.GlobalMaxPooling1D()(x)
x = layers.Dense(128)(x)
x = layers.Activation('relu')(x)
x = layers.Dense(64)(x)
x = layers.Activation('relu')(x)
x = layers.Dense(num_classes)(x)
outputs = layers.Activation('softmax')(x)

model_3 = tf.keras.Model(inputs, outputs)

model_3.compile(tf.keras.optimizers.Adam(),
                tf.keras.losses.CategoricalCrossentropy(),
                metrics=['accuracy'])

model_3.summary()

train_char_dataset = tf.data.Dataset.from_tensor_slices((train_chars, train_labels_one_hot)).batch(32).prefetch(tf.data.AUTOTUNE)
val_char_dataset = tf.data.Dataset.from_tensor_slices((val_chars, val_labels_one_hot)).batch(32).prefetch(tf.data.AUTOTUNE)

train_char_dataset

#history_char_embed_model_3 = model_3.fit(train_char_dataset, epochs=5, steps_per_epoch=int(0.1 * len(train_char_dataset)))

#model_3.evaluate(val_char_dataset)

#model_3_pred_probs = model_3.predict(val_char_dataset)
#model_3_preds = class_names[tf.argmax(model_3_pred_probs, axis=1)]
#results_model_3 = calculate_results(class_names[tf.argmax(val_labels_one_hot, axis=1)], model_3_preds)
#results_model_3, baseline_results

"""###CREATING A MIXED MODEL"""

token_inputs = layers.Input(shape=[], dtype=tf.string, name='token_input')
token_embeddings = EmbedLayer()(token_inputs)
token_outputs = layers.Dense(128, activation='relu')(token_embeddings)

token_model = tf.keras.Model(token_inputs, token_outputs)

char_inputs = layers.Input(shape=[], dtype=tf.string, name='char_input')
char_vectors = char_vectorizer(char_inputs)
char_embeddings = char_embedding(char_vectors)
char_bi_lstm = layers.Bidirectional(layers.LSTM(24))(char_embeddings)

char_model = tf.keras.Model(char_inputs, char_bi_lstm)

concat_layer = layers.Concatenate()([token_model.output, char_model.output])

dropout_layer_1 = layers.Dropout(0.5)(concat_layer)

dense_layer_1 = layers.Dense(128, 'relu')(dropout_layer_1)

dropout_layer_2 = layers.Dropout(0.5)(dense_layer_1)

output_layer = layers.Dense(num_classes, 'softmax')(dropout_layer_2)

model_4 = tf.keras.Model(inputs=[token_inputs, char_inputs],
                         outputs=output_layer)

model_4.summary()

from keras.utils import plot_model
plot_model(model_4, show_shapes=True)

model_4.compile(tf.keras.optimizers.Adam(),
                tf.keras.losses.CategoricalCrossentropy(),
                metrics=['accuracy'])

train_char_token_data = tf.data.Dataset.from_tensor_slices((train_sentences, train_chars))
train_char_token_labels = tf.data.Dataset.from_tensor_slices(train_labels_one_hot)
train_char_token_dataset = tf.data.Dataset.zip(train_char_token_data, train_char_token_labels)

train_char_token_dataset = train_char_token_dataset.batch(32).prefetch(tf.data.AUTOTUNE)

val_char_token_data = tf.data.Dataset.from_tensor_slices((val_sentences, val_chars))
val_char_token_labels = tf.data.Dataset.from_tensor_slices(val_labels_one_hot)
val_char_token_dataset = tf.data.Dataset.zip(val_char_token_data, val_char_token_labels)

val_char_token_dataset = val_char_token_dataset.batch(32).prefetch(tf.data.AUTOTUNE)

train_char_token_dataset, val_char_token_dataset

#history_hybrid_model_4 = model_4.fit(train_char_token_dataset, epochs=3, steps_per_epoch=int(0.1 * len(train_char_token_dataset)))

#results_model_4 = model_4.evaluate(val_char_token_dataset)

import matplotlib.pyplot as plt
train_df['line_number'].value_counts().plot(kind='bar')

train_lines_one_hot = tf.one_hot(train_df['line_number'].to_numpy(), depth=15)
val_lines_one_hot = tf.one_hot(val_df['line_number'].to_numpy(), depth=15)

train_df['total_lines'].value_counts().plot(kind='bar')

np.percentile(train_df.total_lines, 98)

train_total_lines_one_hot = tf.one_hot(train_df['total_lines'].to_numpy(), depth=20)
val_total_lines_one_hot = tf.one_hot(val_df['line_number'].to_numpy(), depth=20)
test_total_lines_one_hot = tf.one_hot(test_df['line_number'].to_numpy(), depth=20)

"""#CREATING OUR MOST COMPLEX MODEL SO FAR"""

token_inputs = layers.Input(shape=[], dtype="string", name="token_inputs")
token_embeddings = EmbedLayer()(token_inputs)
token_outputs = layers.Dense(128, activation="relu")(token_embeddings)
token_model = tf.keras.Model(inputs=token_inputs,
                             outputs=token_outputs)

# 2. Char inputs
char_inputs = layers.Input(shape=(1,), dtype="string", name="char_inputs")
char_vectors = char_vectorizer(char_inputs)
char_embeddings = EmbedLayer()(char_vectors)
char_bi_lstm = layers.Bidirectional(layers.LSTM(32))(char_embeddings)
char_model = tf.keras.Model(inputs=char_inputs,
                            outputs=char_bi_lstm)

# 3. Line numbers inputs
line_number_inputs = layers.Input(shape=(15,), dtype=tf.int32, name="line_number_input")
x = layers.Dense(32, activation="relu")(line_number_inputs)
line_number_model = tf.keras.Model(inputs=line_number_inputs,
                                   outputs=x)

# 4. Total lines inputs
total_lines_inputs = layers.Input(shape=(20,), dtype=tf.int32, name="total_lines_input")
y = layers.Dense(32, activation="relu")(total_lines_inputs)
total_line_model = tf.keras.Model(inputs=total_lines_inputs,
                                  outputs=y)

# 5. Combine token and char embeddings into a hybrid embedding
combined_embeddings = layers.Concatenate(name="token_char_hybrid_embedding")([token_model.output,
                                                                              char_model.output])
z = layers.Dense(256, activation="relu")(combined_embeddings)
z = layers.Dropout(0.5)(z)

# 6. Combine positional embeddings with combined token and char embeddings into a tribrid embedding
z = layers.Concatenate(name="token_char_positional_embedding")([line_number_model.output,
                                                                total_line_model.output,
                                                                z])

# 7. Create output layer
output_layer = layers.Dense(5, activation="softmax", name="output_layer")(z)

# 8. Put together model
model_5 = tf.keras.Model(inputs=[line_number_model.input,
                                 total_line_model.input,
                                 token_model.input,
                                 char_model.input],
                         outputs=output_layer)

import tensorflow as tf
from tensorflow.keras import layers
import tensorflow_hub as hub

# Define EmbedLayer class
class EmbedLayer(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super(EmbedLayer, self).__init__(**kwargs)
        self.use_layer = hub.KerasLayer(
            "https://tfhub.dev/google/universal-sentence-encoder/4",
            trainable=False,
            name='universal_sentence_encoder',
            dtype=tf.string,
            input_shape=[])

    def call(self, inputs):
        return self.use_layer(inputs)

# Token Model
token_inputs = layers.Input(shape=[], dtype="string", name="token_inputs")
token_embeddings = EmbedLayer()(token_inputs)
token_outputs = layers.Dense(128, activation="relu")(token_embeddings)
token_model = tf.keras.Model(inputs=token_inputs, outputs=token_outputs)

# Char Model
char_inputs = layers.Input(shape=[], dtype="string", name="char_inputs")
char_embeddings = EmbedLayer()(char_inputs)

# Use a Lambda layer to reshape the tensor
char_embeddings = layers.Lambda(lambda x: tf.expand_dims(x, axis=1))(char_embeddings)

# Now the shape should be [batch_size, 1, embedding_dim]
char_bi_lstm = layers.Bidirectional(layers.LSTM(32))(char_embeddings)
char_model = tf.keras.Model(inputs=char_inputs, outputs=char_bi_lstm)

# Line Number Model
line_number_inputs = layers.Input(shape=(15,), dtype=tf.int32, name="line_number_input")
line_number_outputs = layers.Dense(32, activation="relu")(line_number_inputs)
line_number_model = tf.keras.Model(inputs=line_number_inputs, outputs=line_number_outputs)

# Total Lines Model
total_lines_inputs = layers.Input(shape=(20,), dtype=tf.int32, name="total_lines_input")
total_lines_outputs = layers.Dense(32, activation="relu")(total_lines_inputs)
total_line_model = tf.keras.Model(inputs=total_lines_inputs, outputs=total_lines_outputs)

# Combine token and char embeddings into a hybrid embedding
combined_embeddings = layers.Concatenate(name="token_char_hybrid_embedding")([token_model.output, char_model.output])
z = layers.Dense(256, activation="relu")(combined_embeddings)
z = layers.Dropout(0.5)(z)

# Combine positional embeddings with combined token and char embeddings into a tribrid embedding
z = layers.Concatenate(name="token_char_positional_embedding")([line_number_model.output,
                                                                total_line_model.output,
                                                                z])

# Output layer
output_layer = layers.Dense(5, activation="softmax", name="output_layer")(z)

# Final Model
model_5 = tf.keras.Model(inputs=[line_number_model.input,
                                 total_line_model.input,
                                 token_model.input,
                                 char_model.input],
                         outputs=output_layer)

tf.keras.utils.plot_model(model_5)

model_5.compile(tf.keras.optimizers.Adam(),
                tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.2),
                metrics=['accuracy'])

# Create training and validation datasets (all four kinds of inputs)
train_pos_char_token_data = tf.data.Dataset.from_tensor_slices((train_lines_one_hot, # line numbers
                                                                train_total_lines_one_hot, # total lines
                                                                train_sentences, # train tokens
                                                                train_chars)) # train chars
train_pos_char_token_labels = tf.data.Dataset.from_tensor_slices(train_labels_one_hot) # train labels
train_pos_char_token_dataset = tf.data.Dataset.zip((train_pos_char_token_data, train_pos_char_token_labels)) # combine data and labels
train_pos_char_token_dataset = train_pos_char_token_dataset.batch(32).prefetch(tf.data.AUTOTUNE) # turn into batches and prefetch appropriately

# Validation dataset
val_pos_char_token_data = tf.data.Dataset.from_tensor_slices((val_lines_one_hot,
                                                              val_total_lines_one_hot,
                                                              val_sentences,
                                                              val_chars))
val_pos_char_token_labels = tf.data.Dataset.from_tensor_slices(val_labels_one_hot)
val_pos_char_token_dataset = tf.data.Dataset.zip((val_pos_char_token_data, val_pos_char_token_labels))
val_pos_char_token_dataset = val_pos_char_token_dataset.batch(32).prefetch(tf.data.AUTOTUNE) # turn into batches and prefetch appropriately

# Check input shapes
train_pos_char_token_dataset, val_pos_char_token_dataset

history_all_out_model_5 = model_5.fit(train_pos_char_token_dataset, steps_per_epoch=int(0.1 * len(train_pos_char_token_dataset)), epochs=3)

results_model_5 = model_5.evaluate(val_pos_char_token_dataset)

results_model_5

model_5_pred_probs = model_5.predict(val_pos_char_token_dataset, verbose=1)
model_5_pred_probs

model_5_preds = class_names[tf.argmax(model_5_pred_probs, axis=1)]
model_5_preds

class_names[tf.argmax(val_labels_one_hot, axis=1)]

model_5_results = calculate_results(y_true=class_names[tf.argmax(val_labels_one_hot, axis=1)],
                                    y_pred=model_5_preds)
model_5_results
