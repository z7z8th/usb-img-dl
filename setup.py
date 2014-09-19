from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = dict(packages = ["progress", "py_sg"], excludes = [], include_files = ["data/ram_loader-1.0.12.img"])

base = 'Console'

executables = [
    Executable('usb_img_dl.py', base=base, targetName = 'usb_img_dlr')
]

setup(name='usb_img_dlr',
      version = '1.0',
      description = 'infomax usb image downloader',
      options = dict(build_exe = buildOptions),
      executables = executables)
