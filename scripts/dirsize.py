#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from collections import namedtuple


__all__ = ['tree', 'size']

PathInfo = namedtuple("PathInfo", "dirs files")


def warn(msg):
    print(msg, file=sys.stderr)


def tree(start='.', warn=warn):
    flat_tree = {}
    for root, dirs, files, rootfd in os.fwalk(start):
        flat_tree[root] = PathInfo(dirs, files)
        for name in files:
            file_path = os.path.join(root, name)
            try:
                flat_tree[file_path] = os.stat(name, dir_fd=rootfd).st_size
            except EnvironmentError as err:
                warn("WARNING: {} in {}".format(err, root))
    return flat_tree


def size(tree, start, cut=None, warn=warn):
    if cut is not None:
        if cut(start):
            return 0
    try:
        item = tree[start]
    except KeyError:
        warn("WARNING: %s non è nel tree" % start)
        return 0
    if isinstance(item, PathInfo):
        join = os.path.join
        sum_dirs = sum(size(tree, join(start, adir), cut=cut, warn=warn) for adir in item.dirs)
        sum_files = sum(size(tree, join(start, afile), cut=cut, warn=warn) for afile in item.files)
        return sum_dirs + sum_files
    else:
        return item


def humanize_bytes(size, precision=2):
    suffixes = ['B','KB','MB','GB','TB']
    for i, suffix in enumerate(suffixes):
        if size < 1024:
            break
        else:
            size /= 1024
    return "%0.{0}f %s".format(precision) % (size, suffix)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='dirsize calculator')
    parser.add_argument('start', nargs='?', default='.')
    parser.add_argument('-e', '--excludes', help='regex excludes')
    parser.add_argument('-q', '--quiet', action='store_true', help='do not print warnings')
    parser.add_argument('-c', '--tree-cache', help='store and load stats from cache')
    args = parser.parse_args()

    if args.excludes:
        import re
        cut = re.compile(args.excludes).search
    else:
        cut = None

    _warn = warn if not args.quiet else lambda x: None

    size_tree = None
    if args.tree_cache:
        import pickle
        try:
            with open(args.tree_cache, 'rb') as cache_file:
                size_tree = pickle.load(cache_file)
        except EnvironmentError as err:
            warn("Errore caricando la cache: %s" % err)

    if size_tree is None:
        size_tree = tree(args.start, warn=_warn)

    total = size(size_tree, args.start, cut=cut, warn=_warn)

    if args.tree_cache:
        try:
            with open(args.tree_cache, 'wb') as cache_file:
                pickle.dump(size_tree, cache_file)
        except EnvironmentError as err:
            warn("Errore salvando la cache: %s" % err)

    print("%s\t%s" % (humanize_bytes(total), args.start))


if __name__ == "__main__":
    main()
