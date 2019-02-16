import numpy as np

import tensorflow as tf

rnn = tf.contrib.rnn

NUM_RNN_LAYER = 1
RNN_SIZE = [64]


def length(sequence):
  # Measure sentence length by skipping the padded words (-1)
  used = tf.to_float(tf.math.greater_equal(sequence, 0))
  length = tf.reduce_sum(used, 1)
  length = tf.cast(length, tf.int32)
  return length


def net(x, batch_size, vocab_size, embedding, mode="train"):

  with tf.variable_scope(name_or_scope='seq2label',
                         values=[x],
                         reuse=tf.AUTO_REUSE):

    if mode == "train" or mode == "eval" or mode == 'infer':
      inputs = x
    elif mode == "export":
      pass

    initial_state = ()
    for i_layer in range(NUM_RNN_LAYER):
      initial_state = initial_state + \
        (rnn.LSTMStateTuple(tf.zeros([batch_size, RNN_SIZE[i_layer]], tf.float32),
                            tf.zeros([batch_size, RNN_SIZE[i_layer]], tf.float32)),)

    cell = rnn.MultiRNNCell([rnn.DropoutWrapper(rnn.LSTMCell(num_units=RNN_SIZE[i_layer]),
                                                     output_keep_prob = 0.5)
                            for i_layer in range(NUM_RNN_LAYER)])

    # cell = rnn.MultiRNNCell([rnn.LSTMCell(num_units=RNN_SIZE[i_layer])
    #                         for i_layer in range(NUM_RNN_LAYER)])

    embeddingW = tf.get_variable(
      'embedding',
      initializer=tf.constant(embedding),
      trainable=False)

    # Hack: use only the non-padded words
    sequence_length = length(inputs)

    inputs = inputs + tf.cast(tf.math.equal(inputs, -1), tf.int32)

    input_feature = tf.nn.embedding_lookup(embeddingW, inputs)

    output, _ = tf.nn.dynamic_rnn(
      cell,
      input_feature,
      initial_state=initial_state,
      sequence_length=sequence_length)

    # The last output is the encoding of the entire sentence
    idx_gather = tf.concat(
      [tf.expand_dims(tf.range(tf.shape(output)[0], delta=1), axis=1),
       tf.expand_dims(sequence_length - 1, axis=1)], axis=1)

    last_output = tf.gather_nd(output, indices=idx_gather)

    logits = tf.layers.dense(
      inputs=last_output,
      units=2,
      activation=tf.identity,
      use_bias=True,
      kernel_initializer=tf.contrib.layers.variance_scaling_initializer(2.0),
      bias_initializer=tf.zeros_initializer())

    probabilities = tf.nn.softmax(logits, name='prob')

    return logits, probabilities