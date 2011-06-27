def permalink_builder(wiki, bits):
    bits = list(bits)
    bits[1] = [wiki.name.split('/')[1]] + bits[1]
    return tuple(bits)
