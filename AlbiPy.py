import socket
import json
import threading
import platform

PROBLEMS = ["'", "$", "QH", "?8", "H@", "ZP", "-(", "cX"]

HEADERS = [
    "Id", "UnitPriceSilver", "TotalPriceSilver", "Amount", "Tier",
    "IsFinished", "AuctionType", "HasBuyerFetched", "HasSellerFetched",
    "SellerCharacterId", "SellerName", "BuyerCharacterId", "BuyerName",
    "ItemTypeId", "ItemGroupTypeId", "EnchantmentLevel", "QualityLevel",
    "Expires", "ReferenceId"
]

LOCATIONS = {
    "FOREST_GREEN_MARKETPLACE_PORTAL": "Lymhurst",
    "#FOREST_GREEN_MARKETPLACE_CENTERCITY": "Lymhurst", 
    "#STEPPE_GREEN_MARKETPLACE_CENTERCITY": "Bridgewatch",
    "%HIGHLAND_GREEN_MARKETPLACE_CENTERCITY": "Martlock",
    '"SWAMP_GREEN_MARKETPLACE_CENTERCITY': "Thetford",
    "%MOUNTAIN_GREEN_MARKETPLACE_CENTERCITY": "Fort Sterling",
    "MISTS_GREEN_MARKETPLACE_SMALL": "Brecilien",
    "HIGHLAND_DEAD_MARKETPLACE_CENTERCITY": "Caerleon"
}

def local_ip():
    """Get local IP address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

class datapoint:
    """Single market datapoint including all available data from the game's api"""
    def __init__(self, data):
        # Store raw data
        self.data = data[:]
        
        # Correct silver prices
        data[1] //= 10000
        data[2] //= 10000

        # Set attributes from data indexes
        self.Id = data[0]
        self.UnitPriceSilver = data[1]
        self.TotalPriceSilver = data[2]
        self.Amount = data[3]
        self.Tier = data[4]
        self.IsFinished = data[5]
        self.AuctionType = data[6]
        self.HasBuyerFetched = data[7]
        self.HasSellerFetched = data[8]
        self.SellerCharacterId = data[9]
        self.SellerName = data[10]
        self.BuyerCharacterId = data[11]
        self.BuyerName = data[12]
        self.ItemTypeId = data[13]
        self.ItemGroupTypeId = data[14]
        self.EnchantmentLevel = data[15]
        self.QualityLevel = data[16]
        # self.Expires = data[17]  # Datetime conversion disabled
        self.ReferenceId = data[18]
        self.Location = data[19]

class sniffer_data:
    """Organized sniffed market data"""
    def __init__(self, logs, parsed, malformed):
        self.logs = logs[:]
        self.parsed = parsed[:]
        self.malformed = malformed[:]

    def __getitem__(self, i):
        return self.parsed[i]

    def __len__(self):
        return len(self.parsed)

    def __str__(self):
        parsed = [{HEADERS[j]: attribute for j, attribute in enumerate(i.data)} 
                 for i in self.parsed]
        return json.dumps({
            "logs": self.logs,
            "parsed": parsed,
            "malformed": self.malformed
        })

class sniffing_thread(threading.Thread):
    """Thread class for sniffing market data"""
    def __init__(self, problems=PROBLEMS):
        threading.Thread.__init__(self)
        
        # Initialize attributes
        self.problems = problems
        self.n = 0
        self.e = 0
        self.parsed = []
        self.malformed = []
        self.recording = False
        self.last_parsed = True
        self.logs = [""]  # Log list with placeholder entry

        # Initialize socket based on platform
        if platform.system() != "Windows":
            self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        else:
            self.sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW)
            self.sniffer.bind((local_ip(), 0))
            self.sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    def run(self):
        """Main thread loop for sniffing data"""
        self.recording = True
        self.location = None

        while self.recording:
            # Get market data
            try:
                data = self.sniffer.recvfrom(1350)[0]
            except OSError:
                continue

            # Clean data
            data = str(data)
            for p in self.problems:
                data = data.replace(p, "")

            # Check for location info
            clean_data = [s[3:] for s in data.split("\\") if len(s) > 5]
            for location in LOCATIONS.keys():
                for i in clean_data:
                    if i == location:
                        self.location = LOCATIONS[location]

            # Extract market data chunks
            chunks = [s[3:] for s in data.split("\\") 
                     if len(s) > 5 and ("Silver" in s or "ReferenceId" in s)]

            # Process chunks
            for chunk in chunks:
                if "{" in chunk[:4]:
                    self.logs.append(chunk[chunk.find("{"):])
                elif self.logs:
                    self.logs[-1] += chunk

            self.last_parsed = False

        if not self.last_parsed:
            self.parse_data()

    def parse_data(self):
        """Parse collected market data"""
        self.parsed = []
        self.malformed = []
        
        if not self.logs[0]:
            self.logs.pop(0)
            
        for i, log in enumerate(self.logs):
            try:
                d = list(json.loads(log).values())
                d.append(self.location or "Unknown")
                try:
                    self.parsed.append(datapoint(d))
                except (IndexError, TypeError):
                    self.malformed.append(self.logs[i])
            except json.decoder.JSONDecodeError:
                self.malformed.append(self.logs[i])
                
        self.last_parsed = True

    def get_data(self):
        """Get latest parsed market data"""
        if self.logs == [""]:
            return sniffer_data([], [], [])

        if not self.last_parsed:
            self.parse_data()

        to_return = sniffer_data(self.logs, self.parsed, self.malformed)
        
        # Reset data
        self.logs = [""]
        self.parsed = []
        self.malformed = []
        
        return to_return

    def stop(self):
        """Stop the sniffing thread"""
        self.recording = False
