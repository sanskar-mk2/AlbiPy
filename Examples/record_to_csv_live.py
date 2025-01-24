from AlbiPy import sniffing_thread, HEADERS
from time import sleep


class MarketDataRecorder:
    def __init__(self):
        self.output_filename = None
        self.thread = None

    def write_orders_to_csv(self, orders):
        """Write market orders to CSV file"""
        with open(self.output_filename, "w") as output_file:
            # Write headers
            output_file.write(",".join(HEADERS) + "\n")
            
            # Write order data
            for order in orders:
                output_file.write(",".join(map(str, order.data)) + "\n")

    def start_recording(self):
        """Initialize and start the recording process"""
        self.output_filename = input("Output csv filename: ")
        
        print("Starting sniffing thread...\nHit ctrl-c to stop recording and save results!")
        self.thread = sniffing_thread()
        self.thread.start()

        try:
            while True:
                print("Waiting three seconds...")
                sleep(3)

                print("Fetching recorded orders...")
                orders = self.thread.get_data()

                print(f"Writing recorded orders to {self.output_filename}")
                self.write_orders_to_csv(orders)

        except KeyboardInterrupt:
            self.stop_recording()

    def stop_recording(self):
        """Stop recording and save final data"""
        self.thread.stop()
        print("\nThread stopped!")

        # Save any remaining orders
        final_orders = self.thread.get_data()
        print(f"Writing remaining orders to {self.output_filename}")
        self.write_orders_to_csv(final_orders)


if __name__ == "__main__":
    recorder = MarketDataRecorder()
    recorder.start_recording()
