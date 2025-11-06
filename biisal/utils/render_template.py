from biisal.vars import Var
from biisal.bot import StreamBot
from biisal.utils.human_readable import humanbytes
from biisal.utils.file_properties import get_file_ids
from biisal.server.exceptions import InvalidHash
import urllib.parse
import aiofiles
import logging
import aiohttp
import jinja2

async def render_page(id, secure_hash=None, src=None):
    file = await StreamBot.get_messages(int(Var.BIN_CHANNEL), int(id))
    file_data = await get_file_ids(StreamBot, int(Var.BIN_CHANNEL), int(id))
    # Only validate hash if provided. If you remove hash from links, this allows access by id+filename.
    if secure_hash and file_data.unique_id[:6] != secure_hash:
        logging.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    # Build src. To avoid exposing the hash as a query parameter (e.g. ?hash=...),
    # embed the 6-char secure hash as a short prefix to the id in the path when
    # available. The server routes will accept an optional hash prefix and use
    # it for validation, so this keeps the links clean while preserving security.
    if secure_hash:
        # e.g. https://host/<secure_hash><id>/<filename>
        src_path = f"{secure_hash}{id}/{urllib.parse.quote_plus(file_data.file_name)}"
    else:
        src_path = f"{id}/{urllib.parse.quote_plus(file_data.file_name)}"

    src = urllib.parse.urljoin(Var.URL, src_path)

    tag = file_data.mime_type.split("/")[0].strip()
    file_size = humanbytes(file_data.file_size)
    if tag in ["video", "audio"]:
        template_file = "biisal/template/req.html"
    else:
        template_file = "biisal/template/dl.html"
        async with aiohttp.ClientSession() as s:
            async with s.get(src) as u:
                file_size = humanbytes(int(u.headers.get("Content-Length")))

    with open(template_file) as f:
        template = jinja2.Template(f.read())

    file_name = file_data.file_name.replace("_", " ")

    return template.render(
        file_name=file_name,
        file_url=src,
        file_size=file_size,
        file_unique_id=file_data.unique_id,
    )
