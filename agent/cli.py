from __future__ import annotations

import argparse

from agent.runtime import OfficeAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="OfficePilot CLI")
    parser.add_argument("message", nargs="*", help="要发送的一句话")
    parser.add_argument("--session", default="cli-demo")
    args = parser.parse_args()
    agent = OfficeAgent()
    try:
        if args.message:
            response = agent.chat(args.session, " ".join(args.message))
            print(response["reply"])
            return
        print("OfficePilot CLI，输入 exit 退出。")
        while True:
            message = input("你：").strip()
            if message.lower() in {"exit", "quit"}:
                break
            if message:
                response = agent.chat(args.session, message)
                print("Agent：", response["reply"])
    finally:
        agent.close()


if __name__ == "__main__":
    main()
