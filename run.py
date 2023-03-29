from gui import MainWindow
import argparse
    
def parse_option():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodb", action='store_true', help="For debugging.")
    parser.add_argument("--hand", action='store_true', help="For debugging.")
    return parser.parse_args()
    

if __name__ == "__main__":
    opt = parse_option()
    nodb = opt.__dict__["nodb"]
    hand = opt.__dict__["hand"]
    
    main_window = MainWindow(nodb=nodb, hand=hand)
    main_window.mainloop()