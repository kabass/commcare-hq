import time
from dataclasses import dataclass
from xml.etree import cElementTree as ElementTree

from corehq.apps.users.util import SYSTEM_USER_ID, username_to_user_id
from corehq.form_processor.models import CommCareCase

from .utils import CASEBLOCK_CHUNKSIZE, SYSTEM_FORM_XMLNS, submit_case_blocks


@dataclass(frozen=True)
class SystemFormMeta:
    user_id: str = SYSTEM_USER_ID
    username: str = SYSTEM_USER_ID
    device_id: str = SYSTEM_USER_ID
    xmlns: str = SYSTEM_FORM_XMLNS

    @classmethod
    def for_script(cls, name, username):
        user_id = username_to_user_id(username)
        if not user_id:
            raise Exception(f"User '{username}' not found")

        return cls(
            user_id=user_id,
            username=username,
            device_id=name,
            xmlns=f"http://commcarehq.org/script/{name.split('.')[-1]}",
        )


class CaseBulkDB:
    """
    Context manager to facilitate making case changes in chunks.

    Can optionally wait between each chunk to throttle the form submission rate.
    """

    def __init__(self, domain, form_meta: SystemFormMeta = None, throttle_secs=None):
        self.domain = domain
        self.form_meta = form_meta or SystemFormMeta()
        self.throttle_secs = throttle_secs or 0

    def __enter__(self):
        self.to_save = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commit()

    def save(self, case_block):
        self.to_save.append(case_block)
        if len(self.to_save) >= CASEBLOCK_CHUNKSIZE:
            self.commit()
            if self.throttle_secs:
                time.sleep(self.throttle_secs)

    def commit(self):
        if self.to_save:
            case_blocks = [
                ElementTree.tostring(case_block.as_xml(), encoding='utf-8').decode('utf-8')
                for case_block in self.to_save
            ]
            submit_case_blocks(
                case_blocks,
                self.domain,
                device_id=self.form_meta.device_id,
                xmlns=self.form_meta.xmlns,
                user_id=self.form_meta.user_id,
                username=self.form_meta.username,
            )
            self.to_save = []


def update_cases(domain, update_fn, case_ids, form_meta: SystemFormMeta = None, throttle_secs=None):
    """
    Perform a large number of case updates in chunks

    update_fn should be a function which accepts a case and returns a CaseBlock
    if an update is to be performed, or None to skip the case.
    """
    with CaseBulkDB(domain, form_meta, throttle_secs) as bulk_db:
        for case in CommCareCase.objects.iter_cases(case_ids):
            case_block = update_fn(case)
            if case_block:
                bulk_db.save(case_block)
