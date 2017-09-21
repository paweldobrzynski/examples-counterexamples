from sklearn.exceptions import NotFittedError
from sklearn.metrics import accuracy_score 


class LogisticRegression:
    
  
  def __init__(self,
               n_iter,
               batch_size=1000,
               lmbda=0.0001,
               l1_ratio=0,
               random_state=0,
               learning_rate=0.001,
               momentum=None):
    self.n_iter = n_iter
    self.l1_ratio = l1_ratio
    self.lmbda = lmbda
    self.batch_size = batch_size 
   
    self.optimization_params = {
      "learning_rate": learning_rate 
    }
    if momentum:
      self.optimization_params.update(momentum)
    else:
      self.optimization_params['method'] = 'gradient_descent'
    
    np.random.seed(random_state)
   
    self.is_fitted = False
  
  def fit(self, X, y):
    if self.batch_size:
      n_examples = self.batch_size
    else:
      n_examples = X.shape[0]
    
    n_dim = X.shape[1]
    n_classes = len(np.unique(y))
    
    # inputs
    self.thX = T.dmatrix('thX')
    self.thy = T.vector('thy', dtype='int64')
    
    # weights
    self.thW, self.thB = self.__initialized_weights(n_dim, n_classes)
    
    # calculate probability and loss 
    Z = T.dot(self.thX, self.thW) + self.thB
    self.p_y_by_x = T.nnet.softmax(Z)
    # negative log likelihood
    ll = (T.log(self.p_y_by_x)
          [T.arange(n_examples), self.thy]) 
    nll = - T.mean(ll)
      
    regularization = self.__regularization(self.thW, self.lmbda, self.l1_ratio)
    
    self.loss = nll + regularization
    
    updates = self.__updates(self.optimization_params)
   
    # setup training
    self.train_model = theano.function(
      inputs=[self.thX, self.thy],
      outputs=self.loss,
      updates=updates)
    
    self.__iter_training(self.train_model, X, y, self.n_iter, self.batch_size)
 

  def predict(self, X):
    if self.is_fitted:
      return self.__prediction_function()(X)
    else:
      raise NotFittedError

      
  def score(self, X, y):
    y_pred = self.predict(X)
    return accuracy_score(y, y_pred)
      
       
  def __initialized_weights(self, n_dim, n_classes):
    """
    initialize weights (shared variables)
    """
    
    # initialize class weights
    thW = theano.shared(
        value=np.zeros(
          (n_dim, n_classes),
          dtype=theano.config.floatX),
        name='thW',
        borrow=True)

    # initialize the biases b as a vector of n_out 0s
    thB = theano.shared(
      value=np.zeros(
        (n_classes,),
        dtype=theano.config.floatX),
      name='thB',
      borrow=True)
    return thW, thB
       
    
  def __prediction_function(self):
    """
    actual function used for predicting y given X
    """
    y_pred = T.argmax(self.p_y_by_x, axis=1)
    return theano.function(
      inputs=[self.thX],
      outputs=y_pred)
  
  
  def __regularization(self, W, lmbda, l1_ratio):
    """
    regularization with l1 and l2 weight penalties
    """
    weight_penalty = T.sum(W ** 2)
    l1_penalty = T.sum(abs(W))
    return  (lmbda * 
              ((1 - l1_ratio) * weight_penalty +
               l1_ratio * l1_penalty))
  
  
  def __updates(self, optimization_params):
    """
    choose appropriate updates
    """
    optimization_method = optimization_params['method']
    learning_rate = optimization_params['learning_rate']
    
    if optimization_method == 'gradient_descent':
      return LogisticRegression.__gradient_descent_updates(
        self.loss,
        self.thW,
        self.thB, 
        learning_rate)
    elif optimization_method == 'momentum':
      momentum = optimization_params['decay']
      return LogisticRegression.__momentum_updates(
        self.loss,
        self.thW,
        self.thB,
        learning_rate,
        momentum)
    else:
      raise NotImplementedError("method {} is not implemented".format(optimization_method))
  
  
  def __gradient_descent_updates(loss, W, B, learning_rate):
    """
    gradient descent updates
    """
    
    # gradients
    gW = T.grad(cost=loss, wrt=W)
    gB = T.grad(cost=loss, wrt=B)
      
    updates = [
      (W, W - learning_rate * gW),
      (B, B - learning_rate * gB)]
    return updates

  
  def __momentum_updates(loss, W, B, learning_rate, momentum):
    """
    gradient descent with momentum updates
    """
   
    # gradients
    gW = T.grad(cost=loss, wrt=W)
    gB = T.grad(cost=loss, wrt=B)
    
    # momentum tensor
    velocity_W = theano.shared(
      value=np.zeros(
        W.get_value().shape,
        dtype=theano.config.floatX),
      name='velocity_W',
      borrow=True)
    
    velocity_B = theano.shared(
      value=np.zeros(
        B.get_value().shape,
        dtype=theano.config.floatX),
      name='velocity_B',
      borrow=True)
    
    updates = [
      (velocity_W, momentum * velocity_W - learning_rate * gW),
      (velocity_B, momentum * velocity_B - learning_rate * gB),
      (W, W + velocity_W),
      (B, B + velocity_B)]
    return updates

  
  def __iter_training(self, train_model, X, y, n_iter, batch_size):
    """
    iterate weight updates n_iter times and store loss for each step
    """ 
    def get_batch(batch_size):
      if batch_size:
        indices = np.random.choice(X.shape[0], batch_size, replace=False)
        return X[indices, :], y[indices] 
      else:
        return X, y
      
    self.losses = []
    for __ in range(n_iter):
      X_batch, y_batch = get_batch(batch_size)
      current_loss = train_model(X_batch, y_batch)
      self.losses.append(current_loss)
    
    self.losses = np.array(self.losses)
  
    self.is_fitted = True