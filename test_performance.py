from __future__ import division

from datetime import datetime, timedelta
import os
import model


def test_generic(rootFolder, function):
    rootPath = os.path.abspath(rootFolder)
    head, tail = os.path.split(rootPath)
    start = datetime.now()
    root = function(rootPath)
    end = datetime.now()
    return end-start


def test_iteration(info, maxIterations, rootFolder, function):
    theSum = timedelta(0)
    for i in range(0, maxIterations):
        theSum += test_generic(rootFolder, function)
    if info:
        print(info)
    totalMilliseconds = theSum.microseconds/1000 + 1000*theSum.total_seconds()
    print("{} ({}x): {} ms".format(
        function.__name__,
        maxIterations,
        totalMilliseconds))


def main():
    test_iteration(None, 10, "/usr",
                   model.SystemTreeNode._createSystemTreeRecursive)
    test_iteration(None, 10, "/usr",
                   model.SystemTreeNode._createSystemTreeRecursive2)


if __name__ == "__main__":
    main()
