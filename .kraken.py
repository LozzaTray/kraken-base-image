# ::requirements kraken-std jinja2
# ::pythonpath build-support

import os
import time
import jinja2
from kraken.api import project
from kraken.std.generic.render_file import RenderFileTask
from kraken.std.docker import build_docker_image
from kraken.std.docker.manifest_tool import ManifestToolPushTask
from pyenv_docker import render_pyenv_dockerfile


def render_dockerfile() -> str:
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(project.directory))
    jinja_env.globals["pyenv"] = render_pyenv_dockerfile
    template = jinja_env.get_template("Dockerfile.template")
    return template.render()


def get_docker_auth() -> dict[str, tuple[str, str]]:
    username, password = os.getenv("GITHUB_USER"), os.getenv("GITHUB_PASSWORD")
    if username and password:
        return {"ghcr.io": (username, password)}
    if "CI" in os.environ:
        raise Exception("GITHUB_USER/GITHUB_PASSWORD are required in CI")
    return {}


def docker_config(dockerfile: RenderFileTask, platform: str) -> None:
    image = f"ghcr.io/kraken-build/kraken-base-image"
    tag = "develop"
    auth = get_docker_auth()
    build_docker_image(
        name=f"buildDocker-{platform}",
        backend="kaniko",
        dockerfile=dockerfile.file,
        auth=auth,
        tags=[f"{image}/{platform}:{tag}"],
        platform=platform,
        build_args={"CACHE_BUSTER": str(time.time()), "ARCH": platform.split("/")[1]},
        cache_repo=f"{image}/cache" if auth else None,
        load=False if auth else True,
        push=True if auth else False,
    )


dockerfile = project.do(
    "renderDockerfile",
    RenderFileTask,
    file=project.build_directory / "Dockerfile",
    content=render_dockerfile,
)

docker_config(dockerfile, "linux/arm64")
docker_config(dockerfile, "linux/amd64")
project.do("buildDocker-multi", ManifestToolPushTask,
