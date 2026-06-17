import { useEffect, useState, useRef } from 'react';
import protobuf from 'protobufjs';

const protoStr = `
syntax = "proto3";
message PricingData {
  string id = 1;
  float price = 2;
  sint64 time = 3;
  string currency = 4;
  string exchange = 5;
  int32 quoteType = 6;
  int32 marketHours = 7;
  float changePercent = 8;
  sint64 dayVolume = 9;
  float dayHigh = 10;
  float dayLow = 11;
  float change = 12;
  string shortName = 13;
  sint64 expireDate = 14;
  float openPrice = 15;
  float previousClose = 16;
  float strikePrice = 17;
  string underlyingSymbol = 18;
  sint64 openInterest = 19;
  sint64 optionsType = 20;
  sint64 miniOption = 21;
  sint64 lastSize = 22;
  float bid = 23;
  sint64 bidSize = 24;
  float ask = 25;
  sint64 askSize = 26;
  sint64 priceHint = 27;
  sint64 vol_24hr = 28;
  sint64 volAllCurrencies = 29;
  string fromcurrency = 30;
  string lastMarket = 31;
  double circulatingSupply = 32;
  double marketcap = 33;
}
`;

const root = protobuf.parse(protoStr).root;
const PricingData = root.lookupType("PricingData");

function base64ToUint8Array(base64: string) {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

export interface LivePriceData {
  id: string;
  price: number;
  time: number;
  change: number;
  changePercent: number;
  dayVolume: number;
  dayHigh: number;
  dayLow: number;
}

export const useLivePrice = (symbol: string) => {
  const [liveData, setLiveData] = useState<LivePriceData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!symbol) return;

    // Format ticker for Yahoo Finance (NSE stocks need .NS suffix)
    let yfTicker = symbol;
    if (symbol !== "AAPL" && symbol !== "MSFT" && symbol !== "TSLA" && symbol !== "NVDA" && 
        symbol !== "AMZN" && symbol !== "GOOGL" && symbol !== "META") {
      yfTicker = symbol === "MSTC" ? "MSTCLTD.NS" : `${symbol}.NS`;
    }

    const connect = () => {
      const ws = new WebSocket('wss://streamer.finance.yahoo.com');
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        ws.send(JSON.stringify({ subscribe: [yfTicker] }));
      };

      ws.onmessage = (event) => {
        try {
          const buffer = base64ToUint8Array(event.data);
          const decoded = PricingData.decode(buffer) as unknown as LivePriceData;
          if (decoded && decoded.id === yfTicker) {
            setLiveData({
              id: decoded.id,
              price: decoded.price,
              time: decoded.time,
              change: decoded.change,
              changePercent: decoded.changePercent,
              dayVolume: decoded.dayVolume,
              dayHigh: decoded.dayHigh,
              dayLow: decoded.dayLow,
            });
          }
        } catch (err) {
          console.error("Failed to decode Yahoo Finance protobuf", err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt to reconnect after 5 seconds
        setTimeout(connect, 5000);
      };

      ws.onerror = (err) => {
        console.error("Yahoo WebSocket Error:", err);
      };
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [symbol]);

  return { liveData, isConnected };
};
