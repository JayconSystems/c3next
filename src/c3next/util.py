from Crypto.Hash import CMAC
from Crypto.Cipher import AES

from c3next.config import MASTER_KEY


def evolve_dk(dk, mask, num):
    # Evolve the DK. Same algo as the "beacon", but we know we'll
    # be masking the unknown bits, so shift in zeros
    h, l = dk >> 16, dk & 0x0000ffff
    m_h, m_l = mask >> 16, mask & 0x0000ffff
    if num == 0:
        l = (l << 1) & 0xffff
        m_l = m_l << 1 & 0xffff
        if num == 1:
            h = h << 1 & 0xffff
            m_h = m_h << 1
    dk = (h << 16) | l & 0xffff
    mask = (m_h << 16) | m_l
    return (dk, mask)


def derive_key(b_id):
    cmac = CMAC.new(MASTER_KEY, ciphermod=AES)
    cmac.update(b_id)
    return cmac.digest()


def ceildiv(a, b):
    return -(-a // b)
