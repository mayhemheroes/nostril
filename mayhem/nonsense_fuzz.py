#!/usr/bin/python3
import atheris
import sys

with atheris.instrument_imports():
    from nostril import nonsense

def testOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    n_str = fdp.ConsumeUnicodeNoSurrogates(64)

    try:
        nonsense(n_str)
    except ValueError:
        pass
        
def main():
    atheris.Setup(sys.argv, testOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()