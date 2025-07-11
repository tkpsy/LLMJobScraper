#!/bin/bash

# Docker環境の起動・操作スクリプト

set -e

# 色付きの出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 環境変数チェック
check_env() {
    if [ ! -f .env ]; then
        print_error ".envファイルが見つかりません"
        print_info ".env.exampleをコピーして.envファイルを作成してください"
        exit 1
    fi
}

# コンテナビルド
build() {
    print_info "Dockerイメージをビルドしています..."
    docker-compose build
    print_info "ビルドが完了しました"
}

# コンテナ起動
up() {
    print_info "コンテナを起動しています..."
    docker-compose up -d
    print_info "コンテナが起動しました"
}

# コンテナに入る
shell() {
    print_info "コンテナに入ります..."
    docker-compose exec llm-job-scraper bash
}

# アプリケーション実行
run() {
    print_info "アプリケーションを実行しています..."
    docker-compose exec llm-job-scraper python main.py "$@"
}

# コンテナ停止
down() {
    print_info "コンテナを停止しています..."
    docker-compose down
    print_info "コンテナが停止しました"
}

# 使い方
usage() {
    echo "使い方: $0 [コマンド]"
    echo ""
    echo "コマンド:"
    echo "  build   - Dockerイメージをビルド"
    echo "  up      - コンテナを起動"
    echo "  shell   - コンテナに入る"
    echo "  run     - アプリケーションを実行"
    echo "  down    - コンテナを停止"
    echo "  setup   - 初回セットアップ（build + up）"
    echo ""
    echo "例:"
    echo "  $0 setup          # 初回セットアップ"
    echo "  $0 shell          # コンテナに入ってコマンドを実行"
    echo "  $0 run --auto     # 自動モードで実行"
}

# メイン処理
main() {
    check_env
    
    case "${1:-}" in
        build)
            build
            ;;
        up)
            up
            ;;
        shell)
            shell
            ;;
        run)
            shift
            run "$@"
            ;;
        down)
            down
            ;;
        setup)
            build
            up
            print_info "セットアップ完了！"
            print_info "次のコマンドでコンテナに入れます: $0 shell"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@" 