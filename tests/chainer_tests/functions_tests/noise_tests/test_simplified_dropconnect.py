import unittest

import numpy

import chainer
from chainer import cuda
from chainer import functions
from chainer.functions.noise import simplified_dropconnect
from chainer import gradient_check
from chainer import testing
from chainer.testing import attr
from chainer.testing import condition


@testing.parameterize(*testing.product({
    'x_dtype': [numpy.float16, numpy.float32, numpy.float64],
    'W_dtype': [numpy.float16, numpy.float32, numpy.float64],
    'ratio': [0.0, 0.9],
    'train': [True, False],
}))
class TestSimplifiedDropconnect(unittest.TestCase):

    def setUp(self):
        self.W = numpy.random.uniform(
            -1, 1, (2, 3)).astype(self.W_dtype)
        self.b = numpy.random.uniform(
            -1, 1, 2).astype(self.x_dtype)

        self.x = numpy.random.uniform(-1, 1, (4, 3)).astype(self.x_dtype)
        self.gy = numpy.random.uniform(-1, 1, (4, 2)).astype(self.x_dtype)
        self.y = self.x.dot(self.W.T) + self.b
        self.check_forward_options = {}
        self.check_backward_options = {}
        if self.x_dtype == numpy.float16:
            self.check_forward_options = {'atol': 1e-3, 'rtol': 1e-2}
            self.check_backward_options = {
                'dtype': numpy.float64, 'atol': 5e-4, 'rtol': 5e-3}
        elif self.W_dtype == numpy.float16:
            self.check_backward_options = {
                'dtype': numpy.float64, 'atol': 5e-4, 'rtol': 5e-3}

    def check_forward(self, x_data, W_data, b_data):
        # Check only data type, y is tested by SimplifiedDropconnect link test.
        x = chainer.Variable(x_data)
        W = chainer.Variable(W_data)
        if b_data is None:
            y = functions.simplified_dropconnect(x, W, None,
                                                 ratio=self.ratio,
                                                 train=self.train,
                                                 batchwise_mask=True)
        else:
            b = chainer.Variable(b_data)
            y = functions.simplified_dropconnect(x, W, b,
                                                 ratio=self.ratio,
                                                 train=self.train,
                                                 batchwise_mask=True)
        self.assertEqual(y.data.dtype, self.x_dtype)

    def test_forward_cpu(self):
        self.check_forward(self.x, self.W, self.b)

    def test_forward_cpu_nobias(self):
        self.check_forward(self.x, self.W, None)

    @attr.gpu
    def test_forward_gpu(self):
        self.check_forward(
            cuda.to_gpu(self.x), cuda.to_gpu(self.W), cuda.to_gpu(self.b))

    @attr.gpu
    def test_forward_gpu_nobias(self):
        self.check_forward(
            cuda.to_gpu(self.x), cuda.to_gpu(self.W), None)

    def check_backward(self, x_data, W_data, b_data, y_grad):
        args = x_data, W_data
        if b_data is not None:
            args += (b_data,)

        gradient_check.check_backward(
            simplified_dropconnect.SimplifiedDropconnect(self.ratio, None,
                                                         True),
            args, y_grad, eps=1e-2, **self.check_backward_options)

    @condition.retry(3)
    def test_backward_cpu(self):
        self.check_backward(self.x, self.W, self.b, self.gy)

    @condition.retry(3)
    def test_backward_cpu_nobias(self):
        self.check_backward(self.x, self.W, None, self.gy)

    @attr.gpu
    @condition.retry(3)
    def test_backward_gpu(self):
        self.check_backward(cuda.to_gpu(self.x), cuda.to_gpu(self.W),
                            cuda.to_gpu(self.b), cuda.to_gpu(self.gy))

    @attr.gpu
    @condition.retry(3)
    def test_backward_gpu_nobias(self):
        self.check_backward(cuda.to_gpu(self.x), cuda.to_gpu(self.W),
                            None, cuda.to_gpu(self.gy))


class TestSimplifiedDropconnectBatchwiseMask(unittest.TestCase):

    def setUp(self):
        self.W = numpy.random.uniform(
            -1, 1, (2, 3)).astype(numpy.float32)
        self.b = numpy.random.uniform(
            -1, 1, 2).astype(numpy.float32)

        self.x = numpy.random.uniform(-1, 1, (4, 3)).astype(numpy.float32)
        self.gy = numpy.random.uniform(-1, 1, (4, 2)).astype(numpy.float32)
        self.y = self.x.dot(self.W.T) + self.b
        self.check_forward_options = {}
        self.check_backward_options = {}

    def check_forward(self, x_data, W_data, b_data):
        # Check only data type, y is tested by SimplifiedDropconnect link test.
        x = chainer.Variable(x_data)
        W = chainer.Variable(W_data)
        b = chainer.Variable(b_data)
        func = simplified_dropconnect.SimplifiedDropconnect(0.5, None, True)
        y = func(x, W, b)
        self.assertEqual(y.data.dtype, numpy.float32)
        self.assertEqual(func.mask.shape, (x.shape[0],) + W.shape)

    def test_forward_cpu(self):
        self.check_forward(self.x, self.W, self.b)

    @attr.gpu
    def test_forward_gpu(self):
        self.check_forward(
            cuda.to_gpu(self.x), cuda.to_gpu(self.W), cuda.to_gpu(self.b))


class TestSimplifiedDropconnectNotBatchwiseMask(unittest.TestCase):

    def setUp(self):
        self.W = numpy.random.uniform(
            -1, 1, (2, 3)).astype(numpy.float32)
        self.b = numpy.random.uniform(
            -1, 1, 2).astype(numpy.float32)

        self.x = numpy.random.uniform(-1, 1, (4, 3)).astype(numpy.float32)
        self.gy = numpy.random.uniform(-1, 1, (4, 2)).astype(numpy.float32)
        self.y = self.x.dot(self.W.T) + self.b
        self.check_forward_options = {}
        self.check_backward_options = {}

    def check_forward(self, x_data, W_data, b_data):
        # Check only data type, y is tested by SimplifiedDropconnect link test.
        x = chainer.Variable(x_data)
        W = chainer.Variable(W_data)
        b = chainer.Variable(b_data)
        func = simplified_dropconnect.SimplifiedDropconnect(0.5, None, False)
        y = func(x, W, b)
        self.assertEqual(y.data.dtype, numpy.float32)
        self.assertEqual(func.mask.shape, W.shape)

    def test_forward_cpu(self):
        self.check_forward(self.x, self.W, self.b)

    @attr.gpu
    def test_forward_gpu(self):
        self.check_forward(
            cuda.to_gpu(self.x), cuda.to_gpu(self.W), cuda.to_gpu(self.b))

    def check_backward(self, x_data, W_data, b_data, y_grad):
        args = x_data, W_data
        args = args + (b_data,)

        gradient_check.check_backward(
            simplified_dropconnect.SimplifiedDropconnect(0.5, None, True),
            args, y_grad, eps=1e-2, **self.check_backward_options)

    @condition.retry(3)
    def test_backward_cpu(self):
        self.check_backward(self.x, self.W, self.b, self.gy)

    @attr.gpu
    @condition.retry(3)
    def test_backward_gpu(self):
        self.check_backward(cuda.to_gpu(self.x), cuda.to_gpu(self.W),
                            cuda.to_gpu(self.b), cuda.to_gpu(self.gy))


testing.run_module(__name__, __file__)