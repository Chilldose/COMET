import numpy as np
from numpy.linalg import inv

class transformation:
    """Class which handles afine transformations in 3 dimensions for handling sensor to jig coordinate systems"""

    def __init__(self):
        pass

    def transformation_matrix(self, s1, s2, s3, t1, t2, t3):
        """Calculates the transformation matrix of the system.
        Via the equation T = P^-1 Q where P and Q are coming from the linear system s*T + V0 = v
        si are the corresponding vectors (coordinates) in the sensor system, ti are those from the table system.
        They must be numpy arrays.
        """

        s1 = np.array(s1)
        s2 = np.array(s2)
        s3 = np.array(s3)
        t1 = np.array(t1)
        t2 = np.array(t2)
        t3 = np.array(t3)

        Q = np.array(
            [
                [t2[0] - t1[0], t2[1] - t1[1], t2[2] - t1[2]],
                [t3[0] - t1[0], t3[1] - t1[1], t3[2] - t1[2]],
            ]
        )

        P = np.array([[s2[0] - s1[0], s2[1] - s1[1]], [s3[0] - s1[0], s3[1] - s1[1]]])

        try:
            # Invert the P matrix
            Pinv = inv(P)

            # Build the dot product
            T = np.dot(Pinv, Q)

            # Offset
            V0 = np.subtract(t2, np.transpose(s2[0:2]).dot(T))
        except Exception as e:
            return -1, -1

        return T, V0

    def vector_trans(self, v, T, V0):
        """This function transforms a Vector from the sensor system to the table system by vs*T+V0=vt"""
        v = np.array(v)
        return np.add(v[0:2].dot(T), V0)

if __name__ == "__main__":
    trans = transformation()
    t, V = trans.transformation_matrix([0,0,0], [0,100,0], [100,100, 0], [1,1,1], [1,111,10], [101,101,20])
    print(t)
    print(V)
    print(trans.vector_trans([0,99,0], t, V))