from hashlib import sha1
from pathlib import Path
import dbm
import logging
import tempfile

from pavilion import wget
from pavilion.unittest import PavTestCase

PAV_DIR = Path(__file__).resolve().parents[2]


class TestWGet(PavTestCase):

    GET_TARGET = "https://github.com/lanl/Pavilion/raw/master/README.md"
    TARGET_HASH = '275fa3c8aeb10d145754388446be1f24bb16fb00'

    _logger = logging.getLogger(__file__)

    def test_get(self):

        # Try to get a configuration from the testing pavilion.yaml file.
        info = wget.head(self.pav_cfg, self.GET_TARGET)

        # Make sure we can pull basic info using an HTTP HEAD. The Etag can
        # change pretty easily; and the content-encoding may muck with the
        # length, so we can't really verify these.
        self.assertIn('Content-Length', info)
        self.assertIn('ETag', info)

        # Note that there are race conditions with this, however,
        # it is unlikely they will ever be encountered in this context.
        dest_fn = Path(tempfile.mktemp(dir='/tmp'))

        # Raises an exception on failure.
        wget.get(self.pav_cfg, self.GET_TARGET, dest_fn)

        self.assertEqual(self.TARGET_HASH,
                         self.get_hash(dest_fn))

        dest_fn.unlink()

    def test_update(self):

        dest_fn = Path(tempfile.mktemp(dir='/tmp'))
        info_fn = dest_fn.with_suffix(dest_fn.suffix + '.info')

        self.assertFalse(dest_fn.exists())
        self.assertFalse(info_fn.exists())

        # Update should get the file if it doesn't exist.
        wget.update(self.pav_cfg, self.GET_TARGET, dest_fn)
        self.assertTrue(dest_fn.exists())
        self.assertTrue(info_fn.exists())

        # It should update the file if the info file isn't there and the
        # sizes don't match.
        ctime = dest_fn.stat().st_ctime
        with dest_fn.open('ab') as dest_file:
            dest_file.write(b'a')
        info_fn.unlink()
        wget.update(self.pav_cfg, self.GET_TARGET, dest_fn)
        new_ctime = dest_fn.stat().st_ctime
        self.assertNotEqual(new_ctime, ctime)
        ctime = new_ctime

        # We'll muck up the info file data, to force an update.
        with dbm.open(str(info_fn), 'w') as db:
            db['ETag'] = 'nope'
            db['Content-Length'] = '-1'
        wget.update(self.pav_cfg, self.GET_TARGET, dest_fn)
        new_ctime = dest_fn.stat().st_ctime
        self.assertNotEqual(new_ctime, ctime)

        dest_fn.stat()
        info_fn.stat()