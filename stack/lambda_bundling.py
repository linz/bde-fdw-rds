import os
import zipfile
from subprocess import check_call
from sys import executable


def lambda_pip_install_requirements(lambda_packaging_out_dir: str, requirements_file: str) -> None:
    # Documentation recommend against calling pip internal api; rather, via command line
    # https://pip.pypa.io/en/latest/user_guide/#using-pip-from-your-program

    check_call(
        [
            executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--force-reinstall",
            f"--target={lambda_packaging_out_dir}",
            f"--requirement={requirements_file}",
        ]
    )


def zip_directory(directory: str, zipfile_handle: zipfile.ZipFile) -> None:
    for path, _directories, files in os.walk(directory):
        for filename in files:
            zip_path = path.replace(directory, "")
            zipfile_handle.write(os.path.join(path, filename), os.path.join(zip_path, filename))


def zip_lambda_assets(lambda_working_dir: str, lambda_directory: str) -> str:
    packaged_lambda = f"{lambda_working_dir}/{lambda_directory}.zip"

    with zipfile.ZipFile(packaged_lambda, "w") as zipped_lambda_assets:
        # python packages
        zip_directory(f"{lambda_working_dir}/packages", zipped_lambda_assets)
        # lambda code
        zip_directory(f"lambda_functions/{lambda_directory}", zipped_lambda_assets)

    return packaged_lambda
