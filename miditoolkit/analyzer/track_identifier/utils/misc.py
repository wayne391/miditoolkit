import os
import numpy as np

def unit_normalize(tensor):
    res = (tensor - np.min(tensor)) / (np.max(tensor) - np.min(tensor))
    return res


def traverse_dir(
                root_dir,
                extension=('mid', 'MID'),
                str_=None,
                is_pure=False,
                verbose=False,
                is_sort=False,
                is_ext=True):
    """
    Evaluate two images. The inputs are specified by file names
    """
    if verbose:
        print('[*] Scanning...')
    file_list = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(extension):
                if str_ is not None:
                    if str_ not in file:
                        continue
                mix_path = os.path.join(root, file)
                pure_path = mix_path[len(root_dir)+1:] if is_pure else mix_path
                if not is_ext:
                    ext = pure_path.split('.')[-1]
                    pure_path = pure_path[:-(len(ext)+1)]
                if verbose:
                    print(pure_path)
                file_list.append(pure_path)
    if verbose:
        print('Total: %d files' % len(file_list))
        print('Done!!!')
    if is_sort:
        file_list.sort()
    return file_list


def diagnose_error(y, y_, file_list, classes):
    print('[*] Error Diagnosis')
    wrong_idx = np.where(y != y_)[0]
    if len(wrong_idx) == 0:
        print('> No Error!')
        return 
    print('> Error Index: {}'.format(str(wrong_idx)))
    print('> Error Files (gt, predicted)')
    for idx in wrong_idx:
        error_fn = file_list[idx]
        print('    >' , error_fn)
        print('     ', classes[y[idx]], classes[y_[idx]])
        print('')
