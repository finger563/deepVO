import tensorflow as tf
from math import ceil
from tensorflow.contrib.rnn import *

class VOModel(object):

    '''Model class of the RCNN for visual odometry.'''

    def __init__(self, image_shape, memory_size, sequence_length):
        '''
        Parameters
        ----------
        image_shape :   tuple
        '''

        with tf.name_scope('inputs'):
            h, w, c = image_shape
            # TODO: Resize images before stacking. Maybe do that outside of the graph?
            self.input_images = tf.placeholder(tf.uint8, shape=[None, sequence_length, h, w, 2 * c],
                                               name='imgs')
            self.target_poses = tf.placeholder(tf.float32, shape=[None, sequence_length, 6],
                                               name='poses')
            self.batch_size   = tf.placeholder(tf.int32, shape=[], name='batch_size')
            self.hidden_state = tf.placeholder(tf.float32, shape=(None, memory_size),
                                               name='hidden_state')
            self.cell_state   = tf.placeholder(tf.float32, shape=(None, memory_size),
                                               name='cell_state')
            self.sequence_length = sequence_length

        with tf.name_scope('cnn'):
            ksizes     = [7,  5,   5,   3,   3,   3,   3,   3,   3]
            strides    = [2,  2,   2,   1,   2,   1,   2,   1,   2]
            n_channels = [64, 128, 256, 256, 512, 512, 512, 512, 1024]
            self.build_cnn(ksizes, strides, n_channels)

        # with tf.name_scope('rnn'):
        #     self.build_rnn(memory_size)

    def build_cnn(self, ksizes, strides, n_channels, use_dropout=False):
        '''Create all the conv layers as specified in the paper.'''

        assert len(ksizes) == len(strides) == len(n_channels), ('Kernel, stride and channel specs '
                                                                'must have same length')

        # biases initialise with a small constant
        bias_initializer = tf.constant_initializer(0.01)

        # kernels initialise according to He et al.
        def kernel_initalizer(k):
            return tf.random_normal_initializer(stddev=np.sqrt(2 / k))

        next_layer_input = self.input_images
        for index, ksize, stride, channels in enumerate(zip(ksizes, strides, n_channels)):
            with tf.name_scope(f'conv{index}'):
                # no relu for last layer
                activation = tf.nn.relu if index < len(ksize) - 1 else None
                next_layer_input = tf.layers.conv2d(next_layer_input,
                                                    channels,
                                                    kernel_size=[ksize, ksize],
                                                    stride=stride,
                                                    padding='SAME',
                                                    activation=activation,
                                                    kernel_initalizer=kernel_initalizer(ksize),
                                                    bias_initializer=bias_initializer)
        self.conv = next_layer_input

    # def build_rnn(self, memory_size, use_dropout=False):
    #     '''Create all recurrent layers as specified in the paper.'''
    #     lstm1           = LSTMCell(memory_size)
    #     lstm2           = LSTMCell(memory_size)
    #     rnn             = MultiRNNCell([lstm1, lstm2])

    #     self.zero_state = rnn.zero_state(self.batch_size, tf.float32)
    #     state           = LSTMStateTuple(c=self.cell_state, h=self.hidden_state)

    #     b, h, w,c = self.conv.get_shape()
    #     conv_outputs = tf.reshape(self.conv, [b, self.sequence_length, h * w * c])
    #     outputs, state  = static_rnn(rnn, conv_outputs, dtype=tf.float32, initial_state=state)
    #     outputs_rehsaped = tf.reshape(outputs, )

    def get_zero_state(self, session, batch_size):
        return session.run(self.zero_state, feed_dict={self.batch_size: batch_size})

    def propagate_input(self, session, input_batch, label_batch, initial_state=None):
        batch_size, sequence_length = input_batch.shape[:2]

        if initial_state is None:
            initial_state = self.get_zero_state(session, batch_size)

        session.run(self.conv, feed_dict={self.input_images: input_batch,
                                          self.target_poses: label_batch,
                                          self.batch_size: batch_size,
                                          self.hidden_state: initial_state.h,
                                          self.cell_state: initial_state.c,
                                          self.sequence_length: sequence_length})
