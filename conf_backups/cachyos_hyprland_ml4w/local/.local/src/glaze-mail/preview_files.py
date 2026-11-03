"""Private preview ownership and cleanup; intentionally standard-library only."""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from pathlib import Path
import os
import re
import secrets
import stat


MAX_BYTES = 16 * 1024 * 1024
NAMESPACE = 'glaze-mail-preview'
PAGES = {'blocked.html', 'images.html'}
HEX_ID = re.compile(r'[0-9a-f]{32}\Z')
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


@dataclass(frozen=True)
class PreviewContext:
    runtime_dir: Path
    invocation_id: str
    unit_name: str


@dataclass(frozen=True)
class AercExport:
    path: Path
    parent_identity: tuple[int, int]
    file_identity: tuple[int, int]
    data: bytes


class _FileLimitError(ValueError):
    def __init__(self, info: os.stat_result) -> None:
        super().__init__('Preview file exceeds its size limit')
        self.info = info


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _names(context: PreviewContext) -> None:
    if not HEX_ID.fullmatch(context.invocation_id):
        raise ValueError('Invalid mail invocation')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@-]{0,230}\.service', context.unit_name):
        raise ValueError('Invalid mail service')
    path = context.runtime_dir
    if not path.is_absolute() or '..' in path.parts or any(c in str(path) for c in '\x00\r\n'):
        raise ValueError('Invalid runtime directory')


def _no_symlinks(path: Path) -> None:
    for parent in (path, *path.parents):
        if stat.S_ISLNK(parent.lstat().st_mode):
            raise ValueError('Symlinked preview paths are not allowed')


def _private_directory(fd: int) -> None:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('Preview directories must be private and owned')


@contextmanager
def _directory(path: Path) -> Iterator[int]:
    _no_symlinks(path)
    try:
        fd = os.open(path, DIR_FLAGS)
    except (NotADirectoryError, IsADirectoryError):
        raise ValueError('Unsafe preview directory') from None
    try:
        _private_directory(fd)
        yield fd
    finally:
        os.close(fd)


def context_from_environment(environ: Mapping[str, str]) -> PreviewContext:
    context = PreviewContext(Path(environ.get('XDG_RUNTIME_DIR', '')),
                             environ.get('INVOCATION_ID', ''),
                             environ.get('GLAZE_MAIL_SERVICE_UNIT', 'glaze-mail-eval.service'))
    _names(context)
    with _directory(context.runtime_dir):
        pass
    return context


def _child(parent: int, name: str, create: bool) -> tuple[int, bool]:
    created = False
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
            created = True
        except FileExistsError:
            pass
    try:
        fd = os.open(name, DIR_FLAGS, dir_fd=parent)
    except NotADirectoryError:
        raise ValueError('Unsafe preview directory') from None
    try:
        _private_directory(fd)
    except BaseException:
        os.close(fd)
        raise
    return fd, created


def _file_info(info: os.stat_result, *, private: bool = True) -> None:
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise ValueError('Preview input must be an owned regular file')
    if private and stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('Preview files must be private')


def _read(parent: int, name: str, limit: int, *, private: bool = True) -> tuple[bytes, os.stat_result]:
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
    except OSError as error:
        if isinstance(error, FileNotFoundError):
            raise
        raise ValueError('Unsafe preview file') from None
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        _file_info(info, private=private)
        if info.st_size > limit:
            raise _FileLimitError(info)
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise _FileLimitError(info)
        return data, info


def _atomic_write(parent: int, name: str, data: bytes) -> None:
    temporary = '.tmp-' + secrets.token_hex(16)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # link is exclusive: never overwrite an unexpected existing target.
        os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
    finally:
        os.unlink(temporary, dir_fd=parent)
    os.fsync(parent)


def _marker(context: PreviewContext) -> bytes:
    return f'{os.getuid()}:{context.invocation_id}\n'.encode('ascii')


@contextmanager
def _invocation(context: PreviewContext, *, create: bool = False, stopping: bool = False) -> Iterator[tuple[int, int, bool]]:
    _names(context)
    with ExitStack() as stack:
        runtime = stack.enter_context(_directory(context.runtime_dir))
        namespace, _ = _child(runtime, NAMESPACE, create)
        stack.callback(os.close, namespace)
        invocation, created = _child(namespace, context.invocation_id, create)
        stack.callback(os.close, invocation)
        if created:
            _atomic_write(invocation, '.owner', _marker(context))
        marked = True
        try:
            data, _ = _read(invocation, '.owner', 128)
            if data != _marker(context):
                raise ValueError('Preview ownership marker does not match')
        except FileNotFoundError:
            if not stopping or os.listdir(invocation):
                raise ValueError('Preview ownership marker is missing') from None
            marked = False
        yield namespace, invocation, marked


def create_preview(source: bytes, context: PreviewContext) -> Path:
    from preview_html import build_documents

    with _invocation(context, create=True) as (_, invocation, _):
        identifier = secrets.token_hex(16)
        os.mkdir(identifier, 0o700, dir_fd=invocation)
        preview, _ = _child(invocation, identifier, False)
        try:
            directory = context.runtime_dir / NAMESPACE / context.invocation_id / identifier
            blocked, images = directory / 'blocked.html', directory / 'images.html'
            documents = build_documents(source, blocked_uri=blocked.as_uri(), images_uri=images.as_uri())
            _atomic_write(preview, 'blocked.html', documents.blocked.encode('utf-8'))
            _atomic_write(preview, 'images.html', documents.images.encode('utf-8'))
        finally:
            os.close(preview)
    return blocked


def validate_preview_path(path: Path, context: PreviewContext) -> Path:
    _names(context)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Invalid preview path')
    try:
        parts = path.relative_to(context.runtime_dir / NAMESPACE / context.invocation_id).parts
    except ValueError:
        raise ValueError('Preview belongs to another location') from None
    if len(parts) != 2 or not HEX_ID.fullmatch(parts[0]) or parts[1] not in PAGES:
        raise ValueError('Only generated preview pages can be opened')
    with _invocation(context) as (_, invocation, _):
        preview, _ = _child(invocation, parts[0], False)
        try:
            _read(preview, parts[1], MAX_BYTES)
        finally:
            os.close(preview)
    return path


def cleanup(context: PreviewContext) -> None:
    try:
        with _invocation(context, stopping=True) as (namespace, invocation, marked):
            names = [name for name in os.listdir(invocation) if name != '.owner']
            for name in names:
                if not HEX_ID.fullmatch(name):
                    raise ValueError('Unexpected entry in preview invocation')
                preview, _ = _child(invocation, name, False)
                try:
                    entries = os.listdir(preview)
                    for entry in entries:
                        if entry not in PAGES and not re.fullmatch(r'\.tmp-[0-9a-f]{32}', entry):
                            raise ValueError('Unexpected file in preview directory')
                        info = os.stat(entry, dir_fd=preview, follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode):
                            if info.st_uid != os.getuid():
                                raise ValueError('Foreign preview symlink')
                        else:
                            _file_info(info)
                    for entry in entries:
                        os.unlink(entry, dir_fd=preview)
                finally:
                    os.close(preview)
                os.rmdir(name, dir_fd=invocation)
            if marked:
                os.unlink('.owner', dir_fd=invocation)
            os.rmdir(context.invocation_id, dir_fd=namespace)
    except FileNotFoundError:
        return


def _export_parent(path: Path) -> Path:
    temporary = Path(os.environ.get('TMPDIR') or '/tmp')
    if (not path.is_absolute() or '..' in path.parts or not temporary.is_absolute() or
            '..' in temporary.parts or path.parent.parent != temporary or
            not re.fullmatch(r'aerc-[A-Za-z0-9_-]+', path.parent.name)):
        raise ValueError('Only private native aerc exports are accepted')
    return path.parent


def read_aerc_export(path: Path) -> AercExport:
    parent = _export_parent(path)
    with _directory(parent) as directory:
        try:
            data, info = _read(directory, path.name, MAX_BYTES, private=False)
        except _FileLimitError as error:
            # Oversized native exports are still transient raw email; dispose only the checked inode.
            discard_export(AercExport(path, _identity(os.fstat(directory)), _identity(error.info), b''))
            raise
        return AercExport(path, _identity(os.fstat(directory)), _identity(info), data)


def discard_export(export: AercExport) -> None:
    parent = _export_parent(export.path)
    with _directory(parent) as directory:
        if _identity(os.fstat(directory)) != export.parent_identity:
            raise ValueError('Export directory changed')
        info = os.stat(export.path.name, dir_fd=directory, follow_symlinks=False)
        _file_info(info, private=False)
        if _identity(info) != export.file_identity:
            raise ValueError('Export file changed')
        os.unlink(export.path.name, dir_fd=directory)
    try:
        parent.rmdir()
    except OSError:
        pass
