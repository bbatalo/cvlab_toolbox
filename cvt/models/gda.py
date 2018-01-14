"""
Grassmann Discriminant Analysis
"""

# Authors: Junki Ishikawa

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import normalize as _normalize, LabelEncoder
import numpy as np

from ..utils import canonical_angle_matrix, subspace_bases


class GrassmannDiscriminantAnalysis(BaseEstimator, ClassifierMixin):
    def __init__(self, n_subdims=3, normalize=True):
        self.normalize = normalize
        self.n_subdims = n_subdims
        self.le = LabelEncoder()
        self.W = None
        self.labels = None
        self.train_X = None
        self.train_projs = None

    def get_params(self, deep=True):
        return {'n_subdims': self.n_subdims, 'normalize': self.normalize}

    def set_params(self, **parameters):
        for parameter, value in parameters.items():
            setattr(self, parameter, value)
        return self

    def fit(self, X, y):
        """
        Fit the model according to the given traininig data and parameters

        Parameters
        ----------
        X: array-like, shape = [n_samples, n_vectors, n_features]
            Training vectors, where n_samples is number of samples, n_vectors is number of vectors on each samples
            and n_features is number of features. Since n_vectors may be variable on each samples, X can be lists
            containing n_sample matrices: [array(n_vectors{1}, n_features),..., array(n_vectors{n_samples}, n_features)]

        y: integer array, shape = [n_samples]
            Target values
        """

        _y = self.le.fit_transform(y)
        self.labels = _y

        n_samples = len(_y)
        n_classes = self.le.classes_.size

        X = self._convert_to_subspace_bases(X)
        self.train_X = X
        C = canonical_angle_matrix(X, X)

        # in-class averages in each class
        uc = np.stack([C[_y == c].mean(axis=0) for c in range(n_classes)], axis=0)
        # an average over all class
        u = C.mean(axis=0)

        # diagonal matrix which has number of samples in each class
        D = np.diag([_y[_y == c].size for c in range(n_classes)])
        # covariances of average over classes
        sigb = (uc - u).T @ D @ (uc - u) / n_samples
        # a sum of inner-covariance
        sigw = (C - uc[_y]).T @ (C - uc[_y]) / n_samples
        # a noise to make sigw full-rank
        sigw += 1e10 * np.eye(n_samples)

        sig = np.linalg.inv(sigw) @ sigb
        _, v = np.linalg.eig(sig)
        self.W = v[:, :n_classes - 1]
        self.train_projs = C.T @ self.W

    def predict(self, X):
        """
        Predict each classes

        Parameters
        ----------
        X: array-like, shape = [n_samples, n_vectors, n_features]
            Predicted vectors, where n_samples is number of samples, n_vectors is number of vectors on each samples
            and n_features is number of features. Since n_vectors may be variable on each samples, X can be lists
            containing n_sample matrices: [array(n_vectors{1}, n_features),..., array(n_vectors{n_samples}, n_features)]

        Returns
        -------
        pred: array-like, shape = [n_samples]
            Predictions
        """

        X = self._convert_to_subspace_bases(X)

        C = canonical_angle_matrix(self.train_X, X)
        projections = C.T @ self.W
        distances = np.linalg.norm(projections[:, np.newaxis, :] - self.train_projs[np.newaxis, :, :], axis=2)
        nearest = np.argmin(distances, axis=1)
        _pred = self.labels[nearest]
        pred = self.le.inverse_transform(_pred)
        return pred

    def _convert_to_subspace_bases(self, X):
        if self.normalize:
            X = [_normalize(x) for x in X]

        X = np.array([subspace_bases(x, self.n_subdims) for x in X])

        return X